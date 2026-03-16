"""FastAPI backend for Short Drama Translation Pipeline prototype."""

import asyncio
import datetime
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import init_db, get_db, Project, Batch, Episode, CharacterDB, PipelineLog, ProjectStatus, StageStatus
from pipeline import run_batch, event_stream, STAGE_CONFIG

app = FastAPI(title="Short Drama Translation Pipeline", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    init_db()


# === Schemas ===

class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    total_episodes: int = 50
    batch_size: int = 10
    target_language: str = "en"

class BatchAction(BaseModel):
    batch_id: int


# === Project Endpoints ===

@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    projects = db.query(Project).order_by(Project.created_at.desc()).all()
    result = []
    for p in projects:
        batch_count = db.query(Batch).filter(Batch.project_id == p.id).count()
        completed_batches = db.query(Batch).filter(Batch.project_id == p.id, Batch.status == ProjectStatus.COMPLETED).count()
        total_eps = db.query(Episode).filter(Episode.batch_id.in_(
            db.query(Batch.id).filter(Batch.project_id == p.id)
        )).count()
        completed_eps = db.query(Episode).filter(
            Episode.batch_id.in_(db.query(Batch.id).filter(Batch.project_id == p.id)),
            Episode.status == StageStatus.COMPLETED
        ).count()
        result.append({
            "id": p.id, "name": p.name, "description": p.description,
            "total_episodes": p.total_episodes, "batch_size": p.batch_size,
            "target_language": p.target_language, "status": p.status,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "batch_count": batch_count, "completed_batches": completed_batches,
            "total_eps": total_eps, "completed_eps": completed_eps,
        })
    return result


@app.post("/api/projects")
def create_project(data: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        name=data.name, description=data.description,
        total_episodes=data.total_episodes, batch_size=data.batch_size,
        target_language=data.target_language,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Auto-create batches and episodes
    num_batches = (data.total_episodes + data.batch_size - 1) // data.batch_size
    for i in range(num_batches):
        start_ep = i * data.batch_size + 1
        end_ep = min((i + 1) * data.batch_size, data.total_episodes)
        batch = Batch(
            project_id=project.id, batch_number=i + 1,
            start_episode=start_ep, end_episode=end_ep,
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        for ep_num in range(start_ep, end_ep + 1):
            episode = Episode(batch_id=batch.id, episode_number=ep_num)
            db.add(episode)
        db.commit()

    return {"id": project.id, "name": project.name, "batches_created": num_batches}


@app.get("/api/projects/{project_id}")
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    batches = db.query(Batch).filter(Batch.project_id == project_id).order_by(Batch.batch_number).all()
    batch_list = []
    for b in batches:
        ep_count = db.query(Episode).filter(Episode.batch_id == b.id).count()
        completed_count = db.query(Episode).filter(Episode.batch_id == b.id, Episode.status == StageStatus.COMPLETED).count()
        batch_list.append({
            "id": b.id, "batch_number": b.batch_number,
            "start_episode": b.start_episode, "end_episode": b.end_episode,
            "status": b.status, "progress": b.progress,
            "started_at": b.started_at.isoformat() if b.started_at else None,
            "completed_at": b.completed_at.isoformat() if b.completed_at else None,
            "episode_count": ep_count, "completed_count": completed_count,
        })
    characters = db.query(CharacterDB).filter(CharacterDB.project_id == project_id).all()
    char_list = [{"id": c.id, "name": c.name, "aliases": c.aliases, "description": c.description} for c in characters]
    return {
        "id": project.id, "name": project.name, "description": project.description,
        "total_episodes": project.total_episodes, "batch_size": project.batch_size,
        "target_language": project.target_language, "status": project.status,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "batches": batch_list, "characters": char_list,
    }


# === Batch Endpoints ===

@app.post("/api/projects/{project_id}/batches/{batch_id}/start")
async def start_batch(project_id: int, batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(Batch).filter(Batch.id == batch_id, Batch.project_id == project_id).first()
    if not batch:
        raise HTTPException(404, "Batch not found")
    if batch.status == ProjectStatus.PROCESSING:
        raise HTTPException(400, "Batch already processing")

    asyncio.create_task(run_batch(batch_id, project_id))
    return {"message": "Batch processing started", "batch_id": batch_id}


@app.get("/api/projects/{project_id}/batches/{batch_id}/episodes")
def get_batch_episodes(project_id: int, batch_id: int, db: Session = Depends(get_db)):
    episodes = db.query(Episode).filter(Episode.batch_id == batch_id).order_by(Episode.episode_number).all()
    return [{
        "id": e.id, "episode_number": e.episode_number, "title": e.title or f"EP{e.episode_number:03d}",
        "duration_seconds": e.duration_seconds, "status": e.status, "current_stage": e.current_stage,
        "s1_status": e.s1_status, "s2_status": e.s2_status, "s3_status": e.s3_status,
        "s5_status": e.s5_status, "s6_status": e.s6_status, "s7_status": e.s7_status,
        "qa_status": e.qa_status,
        "qa_passed": e.qa_result.get("passed") if e.qa_result else None,
    } for e in episodes]


# === Episode Endpoints ===

@app.get("/api/episodes/{episode_id}")
def get_episode(episode_id: int, db: Session = Depends(get_db)):
    ep = db.query(Episode).filter(Episode.id == episode_id).first()
    if not ep:
        raise HTTPException(404, "Episode not found")
    return {
        "id": ep.id, "episode_number": ep.episode_number, "title": ep.title,
        "duration_seconds": ep.duration_seconds, "status": ep.status,
        "current_stage": ep.current_stage,
        "stages": {
            "s1": ep.s1_status, "s2": ep.s2_status, "s3": ep.s3_status,
            "s5": ep.s5_status, "s6": ep.s6_status, "s7": ep.s7_status,
            "qa": ep.qa_status,
        },
        "subtitle_data": ep.subtitle_data,
        "characters": ep.characters,
        "emotions": ep.emotions,
        "script": ep.script,
        "summary": ep.summary,
        "emotion_analysis": ep.emotion_analysis,
        "hooks": ep.hooks,
        "qa_result": ep.qa_result,
    }


# === Logs ===

@app.get("/api/projects/{project_id}/logs")
def get_logs(project_id: int, limit: int = Query(50, le=200), db: Session = Depends(get_db)):
    logs = db.query(PipelineLog).filter(
        PipelineLog.project_id == project_id
    ).order_by(PipelineLog.timestamp.desc()).limit(limit).all()
    return [{
        "id": l.id, "stage": l.stage, "level": l.level,
        "message": l.message, "timestamp": l.timestamp.isoformat(),
        "episode_id": l.episode_id, "batch_id": l.batch_id,
    } for l in logs]


# === SSE Stream ===

@app.get("/api/projects/{project_id}/stream")
async def stream_events(project_id: int):
    return StreamingResponse(
        event_stream(project_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )


# === Pipeline Config ===

@app.get("/api/pipeline/stages")
def get_pipeline_stages():
    return {
        "stages": {k: {"name": v["name"], "depends_on": v["depends_on"]} for k, v in STAGE_CONFIG.items()},
        "phases": {
            "phase1": {"name": "Phase 1 - 最小闭环", "stages": ["s1", "s2", "s3", "s5"], "active": True},
            "phase2": {"name": "Phase 2 - 翻译约束", "stages": ["s6", "s7", "qa"], "active": True},
            "phase3": {"name": "Phase 3 - 完整版", "stages": ["s4"], "active": False},
        },
    }


# === Stats ===

@app.get("/api/projects/{project_id}/stats")
def get_project_stats(project_id: int, db: Session = Depends(get_db)):
    batch_ids = [b.id for b in db.query(Batch).filter(Batch.project_id == project_id).all()]
    if not batch_ids:
        return {"total_episodes": 0}

    total_eps = db.query(Episode).filter(Episode.batch_id.in_(batch_ids)).count()
    completed_eps = db.query(Episode).filter(Episode.batch_id.in_(batch_ids), Episode.status == StageStatus.COMPLETED).count()

    # Emotion stats from completed episodes
    completed_episodes = db.query(Episode).filter(
        Episode.batch_id.in_(batch_ids),
        Episode.status == StageStatus.COMPLETED,
        Episode.emotion_analysis.isnot(None),
    ).all()

    avg_intensity = 0
    total_reversals = 0
    arc_types = {}
    hook_types = {}
    qa_pass_count = 0

    for ep in completed_episodes:
        if ep.emotion_analysis:
            ea = ep.emotion_analysis
            avg_intensity += ea.get("average_intensity", 0)
            total_reversals += len(ea.get("reversals", []))
            arc = ea.get("arc_type", "unknown")
            arc_types[arc] = arc_types.get(arc, 0) + 1
        if ep.hooks:
            ht = ep.hooks.get("type", "unknown")
            hook_types[ht] = hook_types.get(ht, 0) + 1
        if ep.qa_result and ep.qa_result.get("passed"):
            qa_pass_count += 1

    n = len(completed_episodes) or 1
    return {
        "total_episodes": total_eps,
        "completed_episodes": completed_eps,
        "processing_episodes": db.query(Episode).filter(
            Episode.batch_id.in_(batch_ids), Episode.status == StageStatus.RUNNING
        ).count(),
        "avg_emotion_intensity": round(avg_intensity / n, 1),
        "total_reversals": total_reversals,
        "arc_type_distribution": arc_types,
        "hook_type_distribution": hook_types,
        "qa_pass_rate": round(qa_pass_count / n * 100, 1) if n > 0 else 0,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
