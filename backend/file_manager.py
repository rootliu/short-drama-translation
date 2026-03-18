"""File upload and storage management."""

import os
import shutil
import uuid
from pathlib import Path

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_SUBTITLE_EXT = {".srt", ".ass", ".ssa", ".vtt"}
ALLOWED_VIDEO_EXT = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv", ".webm"}


def get_project_dir(project_id: int) -> Path:
    d = UPLOAD_DIR / str(project_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_upload(project_id: int, filename: str, content: bytes) -> dict:
    """Save an uploaded file and return metadata."""
    ext = Path(filename).suffix.lower()
    file_type = "subtitle" if ext in ALLOWED_SUBTITLE_EXT else "video" if ext in ALLOWED_VIDEO_EXT else "unknown"
    if file_type == "unknown":
        raise ValueError(f"Unsupported file type: {ext}")

    uid = uuid.uuid4().hex[:8]
    safe_name = f"{uid}_{filename}"
    dest = get_project_dir(project_id) / safe_name
    dest.write_bytes(content)

    return {
        "file_id": uid,
        "filename": filename,
        "saved_as": safe_name,
        "path": str(dest),
        "size_bytes": len(content),
        "file_type": file_type,
        "extension": ext,
    }


def read_subtitle_text(path: str) -> str:
    """Read subtitle file content as text, trying common encodings."""
    for encoding in ["utf-8", "utf-8-sig", "gbk", "gb2312", "big5", "shift_jis"]:
        try:
            return Path(path).read_text(encoding=encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    raise ValueError("Could not decode subtitle file with any supported encoding")


def get_upload_path(project_id: int, filename: str) -> Path:
    return get_project_dir(project_id) / filename


def cleanup_project_files(project_id: int):
    d = UPLOAD_DIR / str(project_id)
    if d.exists():
        shutil.rmtree(d)
