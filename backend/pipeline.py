"""Pipeline orchestration with mock processing and SSE progress updates."""

import asyncio
import datetime
import json
import random
from typing import AsyncGenerator
from sqlalchemy.orm import Session

from database import (
    SessionLocal, Project, Batch, Episode, CharacterDB, PipelineLog,
    ProjectStatus, StageStatus
)
from mock_data import generate_episode_data, CHARACTERS

# Global event queues for SSE
_event_queues: dict[int, asyncio.Queue] = {}


def get_event_queue(project_id: int) -> asyncio.Queue:
    if project_id not in _event_queues:
        _event_queues[project_id] = asyncio.Queue()
    return _event_queues[project_id]


async def push_event(project_id: int, event_type: str, data: dict):
    q = get_event_queue(project_id)
    await q.put({"event": event_type, "data": data})


async def event_stream(project_id: int) -> AsyncGenerator[str, None]:
    q = get_event_queue(project_id)
    while True:
        try:
            event = await asyncio.wait_for(q.get(), timeout=30.0)
            yield f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"
        except asyncio.TimeoutError:
            yield f"event: heartbeat\ndata: {json.dumps({'ts': datetime.datetime.utcnow().isoformat()})}\n\n"


def add_log(db: Session, project_id: int, stage: str, message: str,
            batch_id: int = None, episode_id: int = None, level: str = "info", details: dict = None):
    log = PipelineLog(
        project_id=project_id, batch_id=batch_id, episode_id=episode_id,
        stage=stage, level=level, message=message, details=details,
    )
    db.add(log)
    db.commit()


STAGE_CONFIG = {
    "s1": {"name": "S1 字幕校验+说话人", "duration": (1.0, 2.5), "depends_on": []},
    "s2": {"name": "S2 角色识别", "duration": (1.5, 3.0), "depends_on": ["s1"]},
    "s3": {"name": "S3 情绪提取", "duration": (1.5, 3.0), "depends_on": ["s1"]},
    "s5": {"name": "S5 剧本生成", "duration": (2.0, 4.0), "depends_on": ["s2", "s3"]},
    "s6": {"name": "S6 情感管理", "duration": (1.0, 2.0), "depends_on": ["s5"]},
    "s7": {"name": "S7 Hook分析", "duration": (1.0, 2.0), "depends_on": ["s5"]},
    "qa": {"name": "QA 质量校验", "duration": (0.5, 1.5), "depends_on": ["s6", "s7"]},
}


async def process_stage(db: Session, episode: Episode, stage: str, project_id: int, mock_data: dict):
    """Simulate processing a single stage for an episode."""
    config = STAGE_CONFIG[stage]
    status_field = f"{stage}_status"

    # Set running
    setattr(episode, status_field, StageStatus.RUNNING)
    episode.current_stage = stage
    db.commit()

    await push_event(project_id, "stage_update", {
        "episode_id": episode.id,
        "episode_number": episode.episode_number,
        "stage": stage,
        "stage_name": config["name"],
        "status": "running",
    })

    # Simulate processing time
    duration = random.uniform(*config["duration"])
    steps = random.randint(3, 6)
    for step in range(steps):
        await asyncio.sleep(duration / steps)
        progress = round((step + 1) / steps * 100)
        await push_event(project_id, "stage_progress", {
            "episode_id": episode.id,
            "episode_number": episode.episode_number,
            "stage": stage,
            "progress": progress,
        })

    # Apply mock results
    if stage == "s1":
        episode.subtitle_data = mock_data["subtitle_data"]
    elif stage == "s2":
        episode.characters = mock_data["characters"]
    elif stage == "s3":
        episode.emotions = mock_data["emotions"]
    elif stage == "s5":
        episode.script = mock_data["script"]
        episode.summary = mock_data["summary"]
    elif stage == "s6":
        episode.emotion_analysis = mock_data["emotion_analysis"]
    elif stage == "s7":
        episode.hooks = mock_data["hooks"]
    elif stage == "qa":
        episode.qa_result = mock_data["qa_result"]

    # Set completed
    setattr(episode, status_field, StageStatus.COMPLETED)
    db.commit()

    add_log(db, project_id, stage,
            f"EP{episode.episode_number:03d} {config['name']} completed",
            episode_id=episode.id)

    await push_event(project_id, "stage_update", {
        "episode_id": episode.id,
        "episode_number": episode.episode_number,
        "stage": stage,
        "stage_name": config["name"],
        "status": "completed",
    })


async def process_episode(db: Session, episode: Episode, project_id: int):
    """Process all stages for an episode following the DAG."""
    mock_data = generate_episode_data(episode.episode_number - 1)
    episode.title = mock_data["title"]
    episode.duration_seconds = mock_data["duration_seconds"]
    episode.status = StageStatus.RUNNING
    db.commit()

    await push_event(project_id, "episode_start", {
        "episode_id": episode.id,
        "episode_number": episode.episode_number,
        "title": mock_data["title"],
    })

    # S1 first
    await process_stage(db, episode, "s1", project_id, mock_data)

    # S2 and S3 in parallel (both depend on S1)
    await asyncio.gather(
        process_stage(db, episode, "s2", project_id, mock_data),
        process_stage(db, episode, "s3", project_id, mock_data),
    )

    # S5 depends on S2 and S3
    await process_stage(db, episode, "s5", project_id, mock_data)

    # S6 and S7 in parallel (both depend on S5)
    await asyncio.gather(
        process_stage(db, episode, "s6", project_id, mock_data),
        process_stage(db, episode, "s7", project_id, mock_data),
    )

    # QA depends on S6 and S7
    await process_stage(db, episode, "qa", project_id, mock_data)

    episode.status = StageStatus.COMPLETED
    episode.current_stage = "done"
    db.commit()

    await push_event(project_id, "episode_complete", {
        "episode_id": episode.id,
        "episode_number": episode.episode_number,
    })


async def run_batch(batch_id: int, project_id: int):
    """Run the pipeline for an entire batch."""
    db = SessionLocal()
    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return

        batch.status = ProjectStatus.PROCESSING
        batch.started_at = datetime.datetime.utcnow()
        db.commit()

        project = db.query(Project).filter(Project.id == project_id).first()
        if project:
            project.status = ProjectStatus.PROCESSING
            db.commit()

        add_log(db, project_id, "manager",
                f"Batch {batch.batch_number} started (EP{batch.start_episode}-{batch.end_episode})",
                batch_id=batch.id)

        await push_event(project_id, "batch_start", {
            "batch_id": batch.id,
            "batch_number": batch.batch_number,
        })

        episodes = db.query(Episode).filter(Episode.batch_id == batch_id).order_by(Episode.episode_number).all()

        # Process episodes with concurrency limit of 3
        semaphore = asyncio.Semaphore(3)

        async def process_with_limit(ep):
            async with semaphore:
                await process_episode(db, ep, project_id)
                # Update batch progress
                completed = db.query(Episode).filter(
                    Episode.batch_id == batch_id,
                    Episode.status == StageStatus.COMPLETED
                ).count()
                total = len(episodes)
                batch.progress = round(completed / total * 100, 1)
                db.commit()
                await push_event(project_id, "batch_progress", {
                    "batch_id": batch.id,
                    "progress": batch.progress,
                    "completed": completed,
                    "total": total,
                })

        await asyncio.gather(*[process_with_limit(ep) for ep in episodes])

        # Batch complete - populate character DB
        for char in CHARACTERS:
            existing = db.query(CharacterDB).filter(
                CharacterDB.project_id == project_id,
                CharacterDB.name == char["name"]
            ).first()
            if not existing:
                db.add(CharacterDB(
                    project_id=project_id,
                    name=char["name"],
                    aliases=char["aliases"],
                    description=char["description"],
                    first_appearance=1,
                ))

        batch.status = ProjectStatus.COMPLETED
        batch.completed_at = datetime.datetime.utcnow()
        batch.progress = 100.0
        db.commit()

        add_log(db, project_id, "manager",
                f"Batch {batch.batch_number} completed",
                batch_id=batch.id)

        await push_event(project_id, "batch_complete", {
            "batch_id": batch.id,
            "batch_number": batch.batch_number,
        })

    finally:
        db.close()
