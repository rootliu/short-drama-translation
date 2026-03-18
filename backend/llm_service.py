"""Unified LLM service layer wrapping Gemini API with fallback to mock."""

import os
import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Load .env file if present
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for line in _env_path.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_client = None


def _get_client():
    global _client
    if _client is None:
        try:
            from google import genai
            _client = genai.Client(api_key=GEMINI_API_KEY)
        except Exception as e:
            logger.warning(f"Failed to init Gemini client: {e}")
            _client = None
    return _client


async def call_llm(prompt: str, system: str = "", temperature: float = 0.7, max_tokens: int = 4096) -> Optional[str]:
    """Call Gemini API. Returns None if unavailable (caller should fallback to mock)."""
    if not GEMINI_API_KEY:
        logger.info("No GEMINI_API_KEY set, skipping LLM call")
        return None

    client = _get_client()
    if not client:
        return None

    try:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=GEMINI_MODEL,
            contents=full_prompt,
            config={
                "temperature": temperature,
                "max_output_tokens": max_tokens,
            },
        )
        return response.text
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return None


async def call_llm_json(prompt: str, system: str = "", temperature: float = 0.3, max_tokens: int = 4096) -> Optional[dict]:
    """Call LLM and parse response as JSON. Returns None on failure."""
    json_system = (system + "\n\n" if system else "") + "You MUST respond with valid JSON only. No markdown, no code fences, no explanation."
    text = await call_llm(prompt, system=json_system, temperature=temperature, max_tokens=max_tokens)
    if not text:
        return None
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        lines = lines[1:]  # remove opening fence
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON response: {e}\nResponse: {text[:500]}")
        return None


def is_llm_available() -> bool:
    """Check if LLM API is configured and reachable."""
    return bool(GEMINI_API_KEY) and _get_client() is not None
