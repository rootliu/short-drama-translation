"""SRT/ASS subtitle file parser."""

import re
from dataclasses import dataclass, asdict


@dataclass
class SubtitleLine:
    index: int
    start_time: str  # "HH:MM:SS,mmm"
    end_time: str
    start_seconds: float
    end_seconds: float
    text: str
    speaker: str = ""


def _time_to_seconds(t: str) -> float:
    """Convert SRT time format to seconds. Handles both ',' and '.' as ms separator."""
    t = t.replace(",", ".")
    parts = t.split(":")
    h, m = int(parts[0]), int(parts[1])
    s = float(parts[2])
    return h * 3600 + m * 60 + s


def parse_srt(content: str) -> list[dict]:
    """Parse SRT content into structured subtitle data."""
    blocks = re.split(r"\n\s*\n", content.strip())
    lines = []
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        parts = block.split("\n")
        if len(parts) < 3:
            continue
        # First line: index
        try:
            idx = int(parts[0].strip())
        except ValueError:
            continue
        # Second line: timestamps
        time_match = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            parts[1].strip(),
        )
        if not time_match:
            continue
        start_time, end_time = time_match.group(1), time_match.group(2)
        # Remaining lines: text
        text = "\n".join(parts[2:]).strip()
        # Try to extract speaker from common patterns like "Speaker: text" or "[Speaker] text"
        speaker = ""
        speaker_match = re.match(r"^(?:\[(.+?)\]|(.+?)[:：])\s*(.+)$", text, re.DOTALL)
        if speaker_match:
            speaker = (speaker_match.group(1) or speaker_match.group(2)).strip()
            text = speaker_match.group(3).strip()

        line = SubtitleLine(
            index=idx,
            start_time=start_time,
            end_time=end_time,
            start_seconds=_time_to_seconds(start_time),
            end_seconds=_time_to_seconds(end_time),
            text=text,
            speaker=speaker,
        )
        lines.append(asdict(line))
    return lines


def parse_ass(content: str) -> list[dict]:
    """Parse ASS/SSA subtitle content into structured data."""
    lines = []
    in_events = False
    format_fields = []
    idx = 0
    for raw_line in content.split("\n"):
        raw_line = raw_line.strip()
        if raw_line.lower() == "[events]":
            in_events = True
            continue
        if raw_line.startswith("[") and in_events:
            break
        if not in_events:
            continue
        if raw_line.lower().startswith("format:"):
            format_fields = [f.strip().lower() for f in raw_line[7:].split(",")]
            continue
        if not raw_line.lower().startswith("dialogue:"):
            continue
        values = raw_line[9:].split(",", len(format_fields) - 1)
        if len(values) < len(format_fields):
            continue
        row = dict(zip(format_fields, values))
        start = row.get("start", "0:00:00.00")
        end = row.get("end", "0:00:00.00")
        text = row.get("text", "")
        speaker = row.get("name", "") or row.get("actor", "")
        # Clean ASS tags like {\an8}, {\pos(...)}
        text = re.sub(r"\{[^}]*\}", "", text)
        # Replace \N with newline
        text = text.replace("\\N", "\n").replace("\\n", "\n").strip()
        if not text:
            continue
        idx += 1
        # Normalize time format: ASS uses H:MM:SS.cc
        def normalize_time(t):
            parts = t.split(":")
            if len(parts) == 3:
                h = parts[0].zfill(2)
                m = parts[1].zfill(2)
                s_parts = parts[2].split(".")
                s = s_parts[0].zfill(2)
                ms = (s_parts[1] if len(s_parts) > 1 else "0").ljust(3, "0")[:3]
                return f"{h}:{m}:{s},{ms}"
            return t

        start_norm = normalize_time(start)
        end_norm = normalize_time(end)
        lines.append({
            "index": idx,
            "start_time": start_norm,
            "end_time": end_norm,
            "start_seconds": _time_to_seconds(start_norm),
            "end_seconds": _time_to_seconds(end_norm),
            "text": text,
            "speaker": speaker,
        })
    return lines


def parse_subtitle_file(content: str, filename: str) -> list[dict]:
    """Auto-detect format and parse subtitle file."""
    lower = filename.lower()
    if lower.endswith(".ass") or lower.endswith(".ssa"):
        return parse_ass(content)
    return parse_srt(content)


def get_subtitle_stats(lines: list[dict]) -> dict:
    """Compute stats from parsed subtitle lines."""
    if not lines:
        return {"total_lines": 0, "duration": 0, "speakers_detected": 0}
    speakers = set(l["speaker"] for l in lines if l["speaker"])
    max_time = max(l["end_seconds"] for l in lines)
    return {
        "total_lines": len(lines),
        "duration": int(max_time),
        "speakers_detected": len(speakers),
        "speakers": list(speakers),
    }
