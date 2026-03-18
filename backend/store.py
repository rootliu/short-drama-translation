"""
File-system JSON storage layer.

Replaces database.py (SQLite/SQLAlchemy) with plain JSON files on disk.
All project data lives under DATA_DIR (default ./data).

Directory layout per project:

    data/projects/{project_id}/
        project.json
        pipeline_state.json
        character_guide.json
        logs/
            pipeline.log          # JSON-lines (one JSON object per line)
        episodes/
            ep001/
                meta.json
                subtitle.json
                characters.json
                emotions.json
                script.md
                summary.txt
                emotion_analysis.json
                hooks.json
                qa_result.json
"""

from __future__ import annotations

import datetime
import enum
import json
import math
import os
import tempfile
import threading
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = Path(os.environ.get("DATA_DIR", "./data"))

# ---------------------------------------------------------------------------
# Enums (kept identical to the old database.py for API compat)
# ---------------------------------------------------------------------------


class ProjectStatus(str, enum.Enum):
    CREATED = "created"
    PROCESSING = "processing"
    PAUSED = "paused"
    COMPLETED = "completed"


class StageStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


# ---------------------------------------------------------------------------
# Thread-safe low-level helpers
# ---------------------------------------------------------------------------

_lock = threading.Lock()


def _projects_dir() -> Path:
    """Return (and lazily create) the top-level projects directory."""
    d = DATA_DIR / "projects"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _project_dir(project_id: int) -> Path:
    return _projects_dir() / str(project_id)


def _next_id(projects_dir: Path) -> int:
    """Auto-increment project ID by scanning existing directory names."""
    max_id = 0
    if projects_dir.exists():
        for child in projects_dir.iterdir():
            if child.is_dir() and child.name.isdigit():
                max_id = max(max_id, int(child.name))
    return max_id + 1


def _read_json(path: Path) -> dict | list | None:
    """Read a JSON file.  Return *None* when the file does not exist."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def _write_json(path: Path, data: Any) -> None:
    """Write JSON atomically: write to a tmp file then ``os.replace``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        os.replace(tmp_path, path)
    except BaseException:
        # Clean up the temp file on failure
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _write_text(path: Path, text: str) -> None:
    """Write plain text atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, path)
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _read_text(path: Path) -> str | None:
    """Read plain text file.  Return *None* when not found."""
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def _append_log(project_dir: Path, entry: dict) -> None:
    """Append one JSON object as a line to ``logs/pipeline.log``."""
    log_dir = project_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "pipeline.log"
    line = json.dumps(entry, ensure_ascii=False, default=str) + "\n"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(line)


def _episode_dir_name(episode_number: int) -> str:
    """``1`` -> ``ep001``, ``12`` -> ``ep012``, ``999`` -> ``ep999``."""
    return f"ep{episode_number:03d}"


# ---------------------------------------------------------------------------
# Project operations
# ---------------------------------------------------------------------------


def list_projects() -> list[dict]:
    """Return all projects with computed batch/episode counts."""
    pdir = _projects_dir()
    projects: list[dict] = []
    if not pdir.exists():
        return projects

    for child in sorted(pdir.iterdir(), key=lambda p: p.name):
        if not child.is_dir() or not child.name.isdigit():
            continue
        proj = _read_json(child / "project.json")
        if proj is None:
            continue

        # Compute counts from pipeline_state and episode metas
        ps = _read_json(child / "pipeline_state.json") or {"batches": []}
        batches = ps.get("batches", [])
        batch_count = len(batches)
        completed_batches = sum(
            1 for b in batches if b.get("status") == ProjectStatus.COMPLETED.value
        )

        total_eps = proj.get("total_episodes", 0)
        completed_eps = 0
        episodes_dir = child / "episodes"
        if episodes_dir.exists():
            for ep_child in episodes_dir.iterdir():
                if ep_child.is_dir():
                    meta = _read_json(ep_child / "meta.json")
                    if meta and meta.get("status") == StageStatus.COMPLETED.value:
                        completed_eps += 1

        proj["batch_count"] = batch_count
        proj["completed_batches"] = completed_batches
        proj["total_eps"] = total_eps
        proj["completed_eps"] = completed_eps
        projects.append(proj)

    return projects


def create_project(
    name: str,
    description: str = "",
    total_episodes: int = 0,
    batch_size: int = 50,
    target_language: str = "en",
) -> dict:
    """Create a new project with all batch/episode scaffold on disk."""
    with _lock:
        pdir = _projects_dir()
        project_id = _next_id(pdir)
        proj_dir = pdir / str(project_id)
        proj_dir.mkdir(parents=True, exist_ok=True)

        now = datetime.datetime.utcnow().isoformat()

        # --- project.json ---
        project_data = {
            "id": project_id,
            "name": name,
            "description": description,
            "total_episodes": total_episodes,
            "batch_size": batch_size,
            "target_language": target_language,
            "status": ProjectStatus.CREATED.value,
            "created_at": now,
        }
        _write_json(proj_dir / "project.json", project_data)

        # --- batches in pipeline_state.json ---
        num_batches = max(1, math.ceil(total_episodes / batch_size)) if total_episodes > 0 else 0
        batches: list[dict] = []
        for i in range(num_batches):
            start_ep = i * batch_size + 1
            end_ep = min((i + 1) * batch_size, total_episodes)
            batches.append(
                {
                    "batch_number": i + 1,
                    "start_episode": start_ep,
                    "end_episode": end_ep,
                    "status": ProjectStatus.CREATED.value,
                    "progress": 0.0,
                    "started_at": None,
                    "completed_at": None,
                }
            )
        _write_json(proj_dir / "pipeline_state.json", {"batches": batches})

        # --- character_guide.json ---
        _write_json(proj_dir / "character_guide.json", [])

        # --- logs directory ---
        (proj_dir / "logs").mkdir(parents=True, exist_ok=True)

        # --- episode scaffold ---
        episodes_dir = proj_dir / "episodes"
        episodes_dir.mkdir(parents=True, exist_ok=True)
        for ep_num in range(1, total_episodes + 1):
            ep_dir = episodes_dir / _episode_dir_name(ep_num)
            ep_dir.mkdir(parents=True, exist_ok=True)
            meta = {
                "episode_number": ep_num,
                "title": "",
                "duration_seconds": 0,
                "status": StageStatus.PENDING.value,
                "current_stage": "",
                "s1_status": StageStatus.PENDING.value,
                "s2_status": StageStatus.PENDING.value,
                "s3_status": StageStatus.PENDING.value,
                "s5_status": StageStatus.PENDING.value,
                "s6_status": StageStatus.PENDING.value,
                "s7_status": StageStatus.PENDING.value,
                "qa_status": StageStatus.PENDING.value,
                "source_type": "",
                "source_file": "",
            }
            _write_json(ep_dir / "meta.json", meta)

    project_data["batches_created"] = num_batches
    return project_data


def get_project(project_id: int) -> dict | None:
    """Return project.json contents, or *None* if the project doesn't exist."""
    return _read_json(_project_dir(project_id) / "project.json")


def update_project(project_id: int, **fields: Any) -> dict | None:
    """Merge *fields* into an existing project.json and return the result."""
    path = _project_dir(project_id) / "project.json"
    with _lock:
        data = _read_json(path)
        if data is None:
            return None
        data.update(fields)
        _write_json(path, data)
    return data


# ---------------------------------------------------------------------------
# Batch / pipeline-state operations
# ---------------------------------------------------------------------------


def get_pipeline_state(project_id: int) -> dict:
    """Return the full pipeline_state.json (with a ``batches`` list)."""
    return _read_json(_project_dir(project_id) / "pipeline_state.json") or {
        "batches": []
    }


def update_batch_status(project_id: int, batch_number: int, **fields: Any) -> None:
    """Update fields on a specific batch inside pipeline_state.json."""
    path = _project_dir(project_id) / "pipeline_state.json"
    with _lock:
        state = _read_json(path) or {"batches": []}
        for batch in state["batches"]:
            if batch["batch_number"] == batch_number:
                batch.update(fields)
                break
        _write_json(path, state)


def get_batch_episodes(project_id: int, batch_number: int) -> list[dict]:
    """Return episode metas belonging to *batch_number*."""
    state = get_pipeline_state(project_id)
    batch_info: dict | None = None
    for b in state.get("batches", []):
        if b["batch_number"] == batch_number:
            batch_info = b
            break
    if batch_info is None:
        return []

    start = batch_info["start_episode"]
    end = batch_info["end_episode"]
    episodes: list[dict] = []
    for ep_num in range(start, end + 1):
        meta = get_episode_meta(project_id, ep_num)
        if meta:
            # Add qa_passed from qa_result.json if available
            qa = _read_json(get_episode_dir(project_id, ep_num) / "qa_result.json")
            meta["qa_passed"] = qa.get("passed") if isinstance(qa, dict) else None
            episodes.append(meta)
    return episodes


# ---------------------------------------------------------------------------
# Episode operations
# ---------------------------------------------------------------------------


def get_episode_dir(project_id: int, episode_number: int) -> Path:
    """Return the Path to an episode directory (may not exist yet)."""
    return (
        _project_dir(project_id)
        / "episodes"
        / _episode_dir_name(episode_number)
    )


def get_episode_meta(project_id: int, episode_number: int) -> dict | None:
    """Read an episode's meta.json."""
    return _read_json(get_episode_dir(project_id, episode_number) / "meta.json")


def update_episode_meta(project_id: int, episode_number: int, **fields: Any) -> dict | None:
    """Merge *fields* into an episode's meta.json."""
    path = get_episode_dir(project_id, episode_number) / "meta.json"
    with _lock:
        data = _read_json(path)
        if data is None:
            return None
        data.update(fields)
        _write_json(path, data)
    return data


def read_episode_data(
    project_id: int, episode_number: int, filename: str
) -> dict | str | None:
    """Read a stage-output file from an episode directory.

    Returns parsed JSON for ``.json`` files, plain text for ``.md`` / ``.txt``,
    or *None* when the file does not exist.
    """
    ep_dir = get_episode_dir(project_id, episode_number)
    path = ep_dir / filename
    if filename.endswith(".json"):
        return _read_json(path)
    else:
        return _read_text(path)


def write_episode_data(
    project_id: int, episode_number: int, filename: str, data: Any
) -> None:
    """Write stage output into an episode directory.

    ``.md`` and ``.txt`` files are written as plain text; everything else as JSON.
    """
    ep_dir = get_episode_dir(project_id, episode_number)
    ep_dir.mkdir(parents=True, exist_ok=True)
    path = ep_dir / filename
    with _lock:
        if filename.endswith((".md", ".txt")):
            _write_text(path, str(data))
        else:
            _write_json(path, data)


# ---------------------------------------------------------------------------
# Character operations
# ---------------------------------------------------------------------------


def get_characters(project_id: int) -> list[dict]:
    """Return the character guide for a project."""
    return _read_json(_project_dir(project_id) / "character_guide.json") or []


def save_characters(project_id: int, characters: list[dict]) -> None:
    """Overwrite the character guide."""
    with _lock:
        _write_json(_project_dir(project_id) / "character_guide.json", characters)


# ---------------------------------------------------------------------------
# Log operations
# ---------------------------------------------------------------------------


def add_log(
    project_id: int,
    stage: str,
    message: str,
    batch_number: int | None = None,
    episode_number: int | None = None,
    level: str = "info",
) -> None:
    """Append a structured log entry for *project_id*."""
    entry = {
        "project_id": project_id,
        "stage": stage,
        "message": message,
        "level": level,
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }
    if batch_number is not None:
        entry["batch_number"] = batch_number
    if episode_number is not None:
        entry["episode_number"] = episode_number
    with _lock:
        _append_log(_project_dir(project_id), entry)


def get_logs(project_id: int, limit: int = 50) -> list[dict]:
    """Return the last *limit* log entries in reverse-chronological order."""
    log_path = _project_dir(project_id) / "logs" / "pipeline.log"
    if not log_path.exists():
        return []

    # Read all lines then take the tail – simple and sufficient for typical
    # project sizes.  For very large logs a seek-from-end approach would be
    # better, but YAGNI for now.
    lines: list[str] = []
    try:
        with open(log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return []

    result: list[dict] = []
    for idx, line in enumerate(reversed(lines)):
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        # Ensure frontend-expected fields exist
        entry.setdefault("id", len(lines) - idx)
        entry.setdefault("episode_id", entry.get("episode_number"))
        entry.setdefault("batch_id", entry.get("batch_number"))
        result.append(entry)
        if len(result) >= limit:
            break
    return result


# ---------------------------------------------------------------------------
# Stats (computed from files)
# ---------------------------------------------------------------------------


def get_project_stats(project_id: int) -> dict:
    """Compute aggregate statistics matching the frontend ProjectStats shape."""
    proj = get_project(project_id)
    if proj is None:
        return {"total_episodes": 0}

    total_episodes = proj.get("total_episodes", 0)
    episodes_dir = _project_dir(project_id) / "episodes"

    completed_episodes = 0
    processing_episodes = 0
    avg_intensity = 0.0
    total_reversals = 0
    arc_types: dict[str, int] = {}
    hook_types: dict[str, int] = {}
    qa_pass_count = 0
    n_with_stats = 0

    for ep_num in range(1, total_episodes + 1):
        ep_dir = episodes_dir / _episode_dir_name(ep_num)
        meta = _read_json(ep_dir / "meta.json")
        if meta is None:
            continue

        if meta.get("status") == StageStatus.COMPLETED.value:
            completed_episodes += 1
        elif meta.get("status") == StageStatus.RUNNING.value:
            processing_episodes += 1

        # emotion_analysis.json
        ea = _read_json(ep_dir / "emotion_analysis.json")
        if isinstance(ea, dict):
            n_with_stats += 1
            avg_intensity += ea.get("average_intensity", 0)
            total_reversals += len(ea.get("reversals", []))
            arc = ea.get("arc_type", "unknown")
            arc_types[arc] = arc_types.get(arc, 0) + 1

        # hooks.json
        hooks = _read_json(ep_dir / "hooks.json")
        if isinstance(hooks, dict):
            ht = hooks.get("type", "unknown")
            hook_types[ht] = hook_types.get(ht, 0) + 1

        # qa_result.json
        qa = _read_json(ep_dir / "qa_result.json")
        if isinstance(qa, dict) and qa.get("passed"):
            qa_pass_count += 1

    n = n_with_stats or 1
    return {
        "total_episodes": total_episodes,
        "completed_episodes": completed_episodes,
        "processing_episodes": processing_episodes,
        "avg_emotion_intensity": round(avg_intensity / n, 1),
        "total_reversals": total_reversals,
        "arc_type_distribution": arc_types,
        "hook_type_distribution": hook_types,
        "qa_pass_rate": round(qa_pass_count / n * 100, 1) if n > 0 else 0,
    }
