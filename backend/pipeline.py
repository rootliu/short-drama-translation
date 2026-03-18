"""Pipeline orchestration with real AI + mock fallback and SSE progress updates."""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import random
from typing import AsyncGenerator

from store import (
    ProjectStatus,
    StageStatus,
    get_project,
    get_pipeline_state,
    update_batch_status,
    get_episode_meta,
    update_episode_meta,
    read_episode_data,
    write_episode_data,
    get_characters,
    save_characters,
    add_log,
)
from mock_data import generate_episode_data, CHARACTERS
from llm_service import is_llm_available
from stages import (
    ai_s2_character_id,
    ai_s3_emotion,
    ai_s5_translate,
    ai_s6_emotion_analysis,
    ai_s7_hook_analysis,
    ai_qa_review,
)

logger = logging.getLogger(__name__)

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


STAGE_CONFIG = {
    "s1": {"name": "S1 字幕校验+说话人", "duration": (1.0, 2.5), "depends_on": []},
    "s2": {"name": "S2 角色识别", "duration": (1.5, 3.0), "depends_on": ["s1"]},
    "s3": {"name": "S3 情绪提取", "duration": (1.5, 3.0), "depends_on": ["s1"]},
    "s5": {"name": "S5 剧本生成", "duration": (2.0, 4.0), "depends_on": ["s2", "s3"]},
    "s6": {"name": "S6 情感管理", "duration": (1.0, 2.0), "depends_on": ["s5"]},
    "s7": {"name": "S7 Hook分析", "duration": (1.0, 2.0), "depends_on": ["s5"]},
    "qa": {"name": "QA 质量校验", "duration": (0.5, 1.5), "depends_on": ["s6", "s7"]},
}


async def process_stage(
    project_id: int, ep_num: int, stage: str, mock_data: dict
):
    """Process a single stage: try real AI first, fallback to mock."""
    config = STAGE_CONFIG[stage]
    use_ai = is_llm_available()

    # Set running
    update_episode_meta(project_id, ep_num, **{f"{stage}_status": "running", "current_stage": stage})

    await push_event(project_id, "stage_update", {
        "episode_id": ep_num,
        "episode_number": ep_num,
        "stage": stage,
        "stage_name": config["name"],
        "status": "running",
        "mode": "ai" if use_ai else "mock",
    })

    # Get the dialogue data for AI stages
    dialogues = []
    raw_subs = read_episode_data(project_id, ep_num, "raw_subtitles.json")
    if raw_subs:
        dialogues = raw_subs
    else:
        subtitle_data = read_episode_data(project_id, ep_num, "subtitle.json")
        if subtitle_data and "dialogues" in subtitle_data:
            dialogues = subtitle_data["dialogues"]

    # Get project target language
    project = get_project(project_id)
    target_lang = project.get("target_language", "en") if project else "en"

    ai_result = None

    if use_ai and stage != "s1":  # S1 is handled by upload/parser, skip AI for it
        try:
            if stage == "s2" and dialogues:
                ai_result = await ai_s2_character_id(dialogues)
            elif stage == "s3" and dialogues:
                ai_result = await ai_s3_emotion(dialogues)
            elif stage == "s5" and dialogues:
                characters = read_episode_data(project_id, ep_num, "characters.json") or []
                emotions = read_episode_data(project_id, ep_num, "emotions.json") or {}
                ai_result = await ai_s5_translate(
                    dialogues, characters, emotions, target_lang
                )
            elif stage == "s6":
                emotions = read_episode_data(project_id, ep_num, "emotions.json") or {}
                ai_result = await ai_s6_emotion_analysis(dialogues, emotions)
            elif stage == "s7":
                summary_text = read_episode_data(project_id, ep_num, "summary.txt")
                script_data = {"summary": summary_text} if summary_text else {}
                ai_result = await ai_s7_hook_analysis(dialogues, script_data)
            elif stage == "qa":
                characters = read_episode_data(project_id, ep_num, "characters.json") or []
                emotion_analysis = read_episode_data(project_id, ep_num, "emotion_analysis.json") or {}
                hooks = read_episode_data(project_id, ep_num, "hooks.json") or {}
                script = read_episode_data(project_id, ep_num, "script.md")
                ep_data = {
                    "dialogues": dialogues,
                    "characters": characters,
                    "emotion_analysis": emotion_analysis,
                    "hooks": hooks,
                    "script": script,
                }
                ai_result = await ai_qa_review(ep_data)
        except Exception as e:
            logger.error(f"AI stage {stage} failed for EP{ep_num}: {e}")
            ai_result = None

    # Send progress events (real AI is instant-ish, but we still show progress)
    if ai_result is None:
        # Mock mode: simulate processing time
        duration = random.uniform(*config["duration"])
        steps = random.randint(3, 6)
        for step in range(steps):
            await asyncio.sleep(duration / steps)
            progress = round((step + 1) / steps * 100)
            await push_event(project_id, "stage_progress", {
                "episode_id": ep_num,
                "episode_number": ep_num,
                "stage": stage,
                "progress": progress,
            })

    # Apply results
    mode = "mock"
    if stage == "s1":
        # S1: if episode already has subtitle_data from upload, keep it; otherwise mock
        existing = read_episode_data(project_id, ep_num, "subtitle.json")
        if not existing:
            write_episode_data(project_id, ep_num, "subtitle.json", mock_data["subtitle_data"])
    elif stage == "s2":
        if ai_result:
            chars = ai_result if isinstance(ai_result, list) else ai_result.get("characters", [])
            write_episode_data(project_id, ep_num, "characters.json", chars)
            mode = "ai"
        else:
            write_episode_data(project_id, ep_num, "characters.json", mock_data["characters"])
    elif stage == "s3":
        if ai_result:
            write_episode_data(project_id, ep_num, "emotions.json", ai_result)
            mode = "ai"
        else:
            write_episode_data(project_id, ep_num, "emotions.json", mock_data["emotions"])
    elif stage == "s5":
        if ai_result:
            write_episode_data(project_id, ep_num, "script.md", ai_result.get("script", ""))
            write_episode_data(project_id, ep_num, "summary.txt", ai_result.get("summary", ""))
            mode = "ai"
        else:
            write_episode_data(project_id, ep_num, "script.md", mock_data["script"])
            write_episode_data(project_id, ep_num, "summary.txt", mock_data["summary"])
    elif stage == "s6":
        if ai_result:
            write_episode_data(project_id, ep_num, "emotion_analysis.json", ai_result)
            mode = "ai"
        else:
            write_episode_data(project_id, ep_num, "emotion_analysis.json", mock_data["emotion_analysis"])
    elif stage == "s7":
        if ai_result:
            write_episode_data(project_id, ep_num, "hooks.json", ai_result)
            mode = "ai"
        else:
            write_episode_data(project_id, ep_num, "hooks.json", mock_data["hooks"])
    elif stage == "qa":
        if ai_result:
            write_episode_data(project_id, ep_num, "qa_result.json", ai_result)
            mode = "ai"
        else:
            write_episode_data(project_id, ep_num, "qa_result.json", mock_data["qa_result"])

    # Set completed
    update_episode_meta(project_id, ep_num, **{f"{stage}_status": "completed"})

    add_log(project_id, stage,
            f"EP{ep_num:03d} {config['name']} completed [{mode}]",
            episode_number=ep_num)

    await push_event(project_id, "stage_update", {
        "episode_id": ep_num,
        "episode_number": ep_num,
        "stage": stage,
        "stage_name": config["name"],
        "status": "completed",
        "mode": mode,
    })


async def process_episode(project_id: int, episode_number: int):
    """Process all stages for an episode following the DAG."""
    mock_data = generate_episode_data(episode_number - 1)

    update_episode_meta(
        project_id, episode_number,
        title=mock_data["title"],
        duration_seconds=mock_data["duration_seconds"],
        status="running",
    )

    await push_event(project_id, "episode_start", {
        "episode_id": episode_number,
        "episode_number": episode_number,
        "title": mock_data["title"],
    })

    # S1 first
    await process_stage(project_id, episode_number, "s1", mock_data)

    # S2 and S3 in parallel (both depend on S1)
    await asyncio.gather(
        process_stage(project_id, episode_number, "s2", mock_data),
        process_stage(project_id, episode_number, "s3", mock_data),
    )

    # S5 depends on S2 and S3
    await process_stage(project_id, episode_number, "s5", mock_data)

    # S6 and S7 in parallel (both depend on S5)
    await asyncio.gather(
        process_stage(project_id, episode_number, "s6", mock_data),
        process_stage(project_id, episode_number, "s7", mock_data),
    )

    # QA depends on S6 and S7
    await process_stage(project_id, episode_number, "qa", mock_data)

    update_episode_meta(project_id, episode_number, status="completed", current_stage="done")

    await push_event(project_id, "episode_complete", {
        "episode_id": episode_number,
        "episode_number": episode_number,
    })


async def run_batch(project_id: int, batch_number: int):
    """Run the pipeline for an entire batch."""
    pipeline_state = get_pipeline_state(project_id)
    if not pipeline_state:
        return

    # Find the batch by batch_number
    batch = None
    for b in pipeline_state.get("batches", []):
        if b.get("batch_number") == batch_number:
            batch = b
            break

    if not batch:
        return

    start_ep = batch["start_episode"]
    end_ep = batch["end_episode"]
    episode_numbers = list(range(start_ep, end_ep + 1))
    total = len(episode_numbers)

    update_batch_status(project_id, batch_number, status="processing", started_at=datetime.datetime.utcnow().isoformat())

    add_log(project_id, "manager",
            f"Batch {batch_number} started (EP{start_ep}-{end_ep})",
            batch_number=batch_number)

    await push_event(project_id, "batch_start", {
        "batch_id": batch_number,
        "batch_number": batch_number,
    })

    # Process episodes with concurrency limit of 3
    semaphore = asyncio.Semaphore(3)

    async def process_with_limit(ep_num: int):
        async with semaphore:
            await process_episode(project_id, ep_num)
            # Update batch progress
            completed = 0
            for en in episode_numbers:
                meta = get_episode_meta(project_id, en)
                if meta and meta.get("status") == "completed":
                    completed += 1
            progress = round(completed / total * 100, 1)
            update_batch_status(project_id, batch_number, progress=progress)
            await push_event(project_id, "batch_progress", {
                "batch_id": batch_number,
                "progress": progress,
                "completed": completed,
                "total": total,
            })

    await asyncio.gather(*[process_with_limit(ep) for ep in episode_numbers])

    # Batch complete - populate character DB
    save_characters(project_id, CHARACTERS)

    update_batch_status(
        project_id, batch_number,
        status="completed",
        completed_at=datetime.datetime.utcnow().isoformat(),
        progress=100.0,
    )

    add_log(project_id, "manager",
            f"Batch {batch_number} completed",
            batch_number=batch_number)

    await push_event(project_id, "batch_complete", {
        "batch_id": batch_number,
        "batch_number": batch_number,
    })
