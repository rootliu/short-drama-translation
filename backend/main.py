"""FastAPI backend for Short Drama Translation Pipeline prototype."""

from __future__ import annotations

import asyncio
import json
from typing import Optional
from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from store import (
    ProjectStatus, StageStatus,
    list_projects, create_project, get_project,
    get_pipeline_state, update_batch_status,
    get_batch_episodes, get_episode_meta, update_episode_meta,
    read_episode_data, write_episode_data,
    get_characters, save_characters,
    add_log, get_logs,
    get_project_stats, get_episode_dir,
)
from pipeline import run_batch, event_stream, STAGE_CONFIG
from file_manager import save_upload, read_subtitle_text, ALLOWED_SUBTITLE_EXT, ALLOWED_VIDEO_EXT
from srt_parser import parse_subtitle_file, get_subtitle_stats
from llm_service import is_llm_available

app = FastAPI(title="Short Drama Translation Pipeline", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Helpers ===

def encode_episode_id(project_id: int, episode_number: int) -> int:
    """Global episode ID = project_id * 10000 + episode_number."""
    return project_id * 10000 + episode_number


def decode_episode_id(episode_id: int) -> tuple[int, int]:
    """Returns (project_id, episode_number) from a global episode ID."""
    return episode_id // 10000, episode_id % 10000


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
def api_list_projects():
    return list_projects()


@app.post("/api/projects")
def api_create_project(data: ProjectCreate):
    result = create_project(
        name=data.name,
        description=data.description,
        total_episodes=data.total_episodes,
        batch_size=data.batch_size,
        target_language=data.target_language,
    )
    return {"id": result["id"], "name": result["name"], "batches_created": result["batches_created"]}


@app.get("/api/projects/{project_id}")
def api_get_project(project_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    pipeline = get_pipeline_state(project_id)
    characters_data = get_characters(project_id)

    # Build batch list with episode counts
    batch_list = []
    for b in pipeline.get("batches", []):
        batch_num = b["batch_number"]
        eps = get_batch_episodes(project_id, batch_num)
        ep_count = len(eps)
        completed_count = sum(1 for e in eps if e.get("status") == StageStatus.COMPLETED)
        batch_list.append({
            "id": batch_num,
            "batch_number": batch_num,
            "start_episode": b.get("start_episode"),
            "end_episode": b.get("end_episode"),
            "status": b.get("status", ProjectStatus.PENDING),
            "progress": b.get("progress", 0),
            "started_at": b.get("started_at"),
            "completed_at": b.get("completed_at"),
            "episode_count": ep_count,
            "completed_count": completed_count,
        })

    char_list = []
    for i, c in enumerate(characters_data):
        char_list.append({
            "id": i + 1,
            "name": c.get("name", ""),
            "aliases": c.get("aliases", []),
            "description": c.get("description", ""),
        })

    return {
        "id": project["id"],
        "name": project["name"],
        "description": project.get("description", ""),
        "total_episodes": project.get("total_episodes"),
        "batch_size": project.get("batch_size"),
        "target_language": project.get("target_language", "en"),
        "status": project.get("status", ProjectStatus.PENDING),
        "created_at": project.get("created_at"),
        "batches": batch_list,
        "characters": char_list,
    }


# === Batch Endpoints ===

@app.post("/api/projects/{project_id}/batches/{batch_id}/start")
async def api_start_batch(project_id: int, batch_id: int):
    project = get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    pipeline = get_pipeline_state(project_id)
    batches = pipeline.get("batches", [])
    batch = None
    for b in batches:
        if b["batch_number"] == batch_id:
            batch = b
            break
    if not batch:
        raise HTTPException(404, "Batch not found")
    if batch.get("status") == ProjectStatus.PROCESSING:
        raise HTTPException(400, "Batch already processing")

    asyncio.create_task(run_batch(project_id, batch_id))
    return {"message": "Batch processing started", "batch_id": batch_id}


@app.get("/api/projects/{project_id}/batches/{batch_id}/episodes")
def api_get_batch_episodes(project_id: int, batch_id: int):
    eps = get_batch_episodes(project_id, batch_id)
    result = []
    for e in eps:
        ep_num = e.get("episode_number", 0)
        ep_id = encode_episode_id(project_id, ep_num)
        result.append({
            "id": ep_id,
            "episode_number": ep_num,
            "title": e.get("title") or f"EP{ep_num:03d}",
            "duration_seconds": e.get("duration_seconds"),
            "status": e.get("status", StageStatus.PENDING),
            "current_stage": e.get("current_stage"),
            "s1_status": e.get("s1_status", StageStatus.PENDING),
            "s2_status": e.get("s2_status", StageStatus.PENDING),
            "s3_status": e.get("s3_status", StageStatus.PENDING),
            "s5_status": e.get("s5_status", StageStatus.PENDING),
            "s6_status": e.get("s6_status", StageStatus.PENDING),
            "s7_status": e.get("s7_status", StageStatus.PENDING),
            "qa_status": e.get("qa_status", StageStatus.PENDING),
            "qa_passed": e.get("qa_passed"),
        })
    return result


# === Episode Endpoints ===

@app.get("/api/projects/{project_id}/episodes/{episode_number}/detail")
def api_get_episode_by_project(project_id: int, episode_number: int):
    """Get episode detail by project_id and episode_number (new-style route)."""
    return _build_episode_response(project_id, episode_number)


@app.get("/api/episodes/{episode_id}")
def api_get_episode(episode_id: int):
    """Get episode by global ID (backward compat). Global ID = project_id * 10000 + episode_number."""
    project_id, episode_number = decode_episode_id(episode_id)
    if project_id <= 0 or episode_number <= 0:
        raise HTTPException(404, "Episode not found")
    return _build_episode_response(project_id, episode_number)


def _build_episode_response(project_id: int, episode_number: int) -> dict:
    meta = get_episode_meta(project_id, episode_number)
    if not meta:
        raise HTTPException(404, "Episode not found")

    ep_id = encode_episode_id(project_id, episode_number)

    # Read rich data files from episode directory
    subtitle_data = read_episode_data(project_id, episode_number, "subtitle.json")
    characters = read_episode_data(project_id, episode_number, "characters.json")
    emotions = read_episode_data(project_id, episode_number, "emotions.json")
    script_text = read_episode_data(project_id, episode_number, "script.md")
    summary_text = read_episode_data(project_id, episode_number, "summary.txt")
    emotion_analysis = read_episode_data(project_id, episode_number, "emotion_analysis.json")
    hooks = read_episode_data(project_id, episode_number, "hooks.json")
    qa_result = read_episode_data(project_id, episode_number, "qa_result.json")

    return {
        "id": ep_id,
        "episode_number": episode_number,
        "title": meta.get("title"),
        "duration_seconds": meta.get("duration_seconds"),
        "status": meta.get("status", StageStatus.PENDING),
        "current_stage": meta.get("current_stage"),
        "stages": {
            "s1": meta.get("s1_status", StageStatus.PENDING),
            "s2": meta.get("s2_status", StageStatus.PENDING),
            "s3": meta.get("s3_status", StageStatus.PENDING),
            "s5": meta.get("s5_status", StageStatus.PENDING),
            "s6": meta.get("s6_status", StageStatus.PENDING),
            "s7": meta.get("s7_status", StageStatus.PENDING),
            "qa": meta.get("qa_status", StageStatus.PENDING),
        },
        "subtitle_data": subtitle_data,
        "characters": characters,
        "emotions": emotions,
        "script": script_text,
        "summary": summary_text,
        "emotion_analysis": emotion_analysis,
        "hooks": hooks,
        "qa_result": qa_result,
    }


# === Logs ===

@app.get("/api/projects/{project_id}/logs")
def api_get_logs(project_id: int, limit: int = Query(50, le=200)):
    logs = get_logs(project_id, limit=limit)
    return logs


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
            "phase1": {"name": "Phase 1 - \u6700\u5c0f\u95ed\u73af", "stages": ["s1", "s2", "s3", "s5"], "active": True},
            "phase2": {"name": "Phase 2 - \u7ffb\u8bd1\u7ea6\u675f", "stages": ["s6", "s7", "qa"], "active": True},
            "phase3": {"name": "Phase 3 - \u5b8c\u6574\u7248", "stages": ["s4"], "active": False},
        },
    }


# === Stats ===

@app.get("/api/projects/{project_id}/stats")
def api_get_project_stats(project_id: int):
    return get_project_stats(project_id)


# === File Upload ===

@app.post("/api/projects/{project_id}/episodes/{episode_id}/upload")
async def upload_episode_file(
    project_id: int,
    episode_id: int,
    file: UploadFile = File(...),
):
    # Decode global episode ID to get episode_number
    _, episode_number = decode_episode_id(episode_id)
    if episode_number <= 0:
        # Maybe episode_id IS the episode_number directly (small number)
        episode_number = episode_id

    meta_check = get_episode_meta(project_id, episode_number)
    if not meta_check:
        raise HTTPException(404, "Episode not found")

    content = await file.read()
    try:
        meta = save_upload(project_id, file.filename, content)
    except ValueError as e:
        raise HTTPException(400, str(e))

    parsed_lines = []

    # If subtitle file, parse immediately
    if meta["file_type"] == "subtitle":
        text = read_subtitle_text(meta["path"])
        lines = parse_subtitle_file(text, file.filename)
        stats = get_subtitle_stats(lines)
        parsed_lines = lines

        subtitle_data = {
            **stats,
            "asr_match_rate": 1.0,
            "dialogues": lines,
        }
        write_episode_data(project_id, episode_number, "subtitle.json", subtitle_data)

        update_episode_meta(project_id, episode_number,
            s1_status=StageStatus.COMPLETED,
            title=meta_check.get("title") or f"EP{episode_number:03d}",
            duration_seconds=stats["duration"],
            source_file=meta["path"],
            source_type=meta["file_type"],
        )
    else:
        update_episode_meta(project_id, episode_number,
            source_file=meta["path"],
            source_type=meta["file_type"],
        )

    return {
        "message": "File uploaded successfully",
        "file": meta,
        "parsed_lines": len(parsed_lines),
    }


@app.post("/api/projects/{project_id}/batch-upload")
async def batch_upload_subtitles(
    project_id: int,
    files: list[UploadFile] = File(...),
):
    """Upload multiple subtitle files at once. Files are matched to episodes by order or filename."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    # Get all episode numbers for this project across all batches
    pipeline = get_pipeline_state(project_id)
    all_episode_numbers = []
    for b in pipeline.get("batches", []):
        for ep_num in range(b["start_episode"], b["end_episode"] + 1):
            all_episode_numbers.append(ep_num)
    all_episode_numbers.sort()

    results = []
    for i, file in enumerate(sorted(files, key=lambda f: f.filename)):
        if i >= len(all_episode_numbers):
            break
        ep_num = all_episode_numbers[i]
        content = await file.read()
        try:
            meta = save_upload(project_id, file.filename, content)
        except ValueError:
            results.append({"filename": file.filename, "status": "error", "reason": "unsupported format"})
            continue

        lines = []
        if meta["file_type"] == "subtitle":
            text = read_subtitle_text(meta["path"])
            lines = parse_subtitle_file(text, file.filename)
            stats = get_subtitle_stats(lines)
            subtitle_data = {**stats, "asr_match_rate": 1.0, "dialogues": lines}
            write_episode_data(project_id, ep_num, "subtitle.json", subtitle_data)
            update_episode_meta(project_id, ep_num,
                s1_status=StageStatus.COMPLETED,
                title=f"EP{ep_num:03d}",
                duration_seconds=stats["duration"],
                source_file=meta["path"],
                source_type=meta["file_type"],
            )
        else:
            update_episode_meta(project_id, ep_num,
                source_file=meta["path"],
                source_type=meta["file_type"],
            )

        results.append({
            "filename": file.filename,
            "episode": ep_num,
            "status": "ok",
            "lines": len(lines) if meta["file_type"] == "subtitle" else 0,
        })

    return {"uploaded": len(results), "results": results}


# === Export ===

@app.get("/api/projects/{project_id}/export")
def export_project_markdown(project_id: int):
    """Export project as a Markdown script document."""
    project = get_project(project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    pipeline = get_pipeline_state(project_id)
    characters_data = get_characters(project_id)

    # Collect completed episodes across all batches
    completed_episodes = []
    for b in pipeline.get("batches", []):
        batch_num = b["batch_number"]
        eps = get_batch_episodes(project_id, batch_num)
        for e in eps:
            if e.get("status") == StageStatus.COMPLETED:
                completed_episodes.append(e)
    completed_episodes.sort(key=lambda e: e.get("episode_number", 0))

    lines = []
    lines.append(f"# {project['name']}\n")
    lines.append(f"> {project.get('description', '')}\n")
    lines.append(f"> Target: {project.get('target_language', 'en').upper()} | Episodes: {len(completed_episodes)} completed\n")
    lines.append("---\n")

    if characters_data:
        lines.append("## Characters\n")
        for c in characters_data:
            aliases = ", ".join(c.get("aliases", [])) if c.get("aliases") else ""
            lines.append(f"- **{c.get('name', '')}** ({aliases}): {c.get('description', '')}")
        lines.append("")

    for ep in completed_episodes:
        ep_num = ep.get("episode_number", 0)
        title = ep.get("title") or "Untitled"
        lines.append(f"## Episode {ep_num} \u2014 {title}\n")

        summary = read_episode_data(project_id, ep_num, "summary.txt")
        if summary:
            lines.append(f"*{summary}*\n")

        emotion_analysis = read_episode_data(project_id, ep_num, "emotion_analysis.json")
        if emotion_analysis and isinstance(emotion_analysis, dict):
            ea = emotion_analysis
            lines.append(f"**Arc**: {ea.get('arc_type', '?')} | **Peak**: {ea.get('peak_time', '?')} | **Avg Intensity**: {ea.get('average_intensity', '?')}/10\n")

        hooks = read_episode_data(project_id, ep_num, "hooks.json")
        if hooks and isinstance(hooks, dict):
            h = hooks
            lines.append(f"**Hook** [{h.get('type', '?')}]: {h.get('content', '')} (attraction: {h.get('attraction_score', '?')}/10)\n")
            if h.get("translation_risk", "LOW") != "LOW":
                lines.append(f"\u26a0\ufe0f Translation Risk: {h.get('translation_risk')} \u2014 {h.get('risk_reason', '')}\n")

        script = read_episode_data(project_id, ep_num, "script.md")
        if script:
            lines.append("### Script\n")
            lines.append(f"```\n{script}\n```\n")

        qa_result = read_episode_data(project_id, ep_num, "qa_result.json")
        if qa_result and isinstance(qa_result, dict):
            qa = qa_result
            status = "\u2705 PASSED" if qa.get("passed") else "\u274c NEEDS REVIEW"
            lines.append(f"**QA**: {status} (score: {qa.get('overall_score', '?')}/10)")
            for issue in qa.get("issues", []):
                lines.append(f"  - \u26a0\ufe0f {issue}")
            lines.append("")

        lines.append("---\n")

    md_content = "\n".join(lines)
    from urllib.parse import quote
    safe_name = quote(f"{project['name']}_script.md")
    return StreamingResponse(
        iter([md_content]),
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_name}"},
    )


# === LLM Status ===

@app.get("/api/system/status")
def system_status():
    return {
        "llm_available": is_llm_available(),
        "supported_formats": {
            "subtitle": list(ALLOWED_SUBTITLE_EXT),
            "video": list(ALLOWED_VIDEO_EXT),
        },
        "pipeline_stages": list(STAGE_CONFIG.keys()),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
