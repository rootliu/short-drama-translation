"""Real AI stage implementations using Gemini API."""

from __future__ import annotations

import json
from llm_service import call_llm_json, call_llm


async def ai_s2_character_id(dialogues: list[dict]) -> list[dict] | None:
    """S2: Use LLM to identify characters from dialogue lines."""
    dialogue_text = "\n".join(
        f"[{d.get('speaker', '?')}]: {d['text']}" for d in dialogues[:50]
    )
    prompt = f"""Analyze the following Chinese short drama dialogue and identify all characters.

For each character, provide:
- name: the character's primary name
- aliases: list of alternative names/titles used
- description: brief character description based on context
- role: one of "protagonist", "antagonist", "supporting", "minor", "narrator"

Dialogue:
{dialogue_text}

Return a JSON array of character objects."""

    result = await call_llm_json(prompt, system="You are a Chinese drama script analyst.")
    if result and isinstance(result, list):
        return result
    if result and isinstance(result, dict) and "characters" in result:
        return result["characters"]
    return None


async def ai_s3_emotion(dialogues: list[dict]) -> dict | None:
    """S3: Use LLM to extract emotions from dialogue lines."""
    dialogue_text = "\n".join(
        f"[{i}] [{d.get('speaker', '?')}]: {d['text']}" for i, d in enumerate(dialogues[:50])
    )
    prompt = f"""Analyze the emotional content of each dialogue line in this Chinese short drama.

For each line, identify:
- emotion: the primary emotion (use Chinese labels like 平和, 愤怒, 悲伤, 喜悦, 震惊, 坚定, 嘲讽, 感动, 紧张, 绝望, etc.)
- score: emotional intensity from 1-10

Also identify:
- peak_emotion: which line has the highest emotional intensity
- average_intensity: average score across all lines

Dialogue:
{dialogue_text}

Return JSON with format:
{{
  "dialogues": [
    {{"index": 0, "speaker": "...", "text": "...", "emotion": "...", "score": N, "confidence": 0.0-1.0}}
  ],
  "peak_emotion": {{"index": N, "speaker": "...", "emotion": "...", "score": N}},
  "average_intensity": N.N
}}"""

    return await call_llm_json(prompt, system="You are an emotion analysis expert for Chinese drama scripts.")


async def ai_s5_translate(dialogues: list[dict], characters: list[dict], emotions: dict, target_language: str = "en") -> dict | None:
    """S5: Context-aware translation with character and emotion awareness."""
    char_info = "\n".join(
        f"- {c['name']} ({', '.join(c.get('aliases', []))}): {c.get('description', '')}"
        for c in characters
    ) if characters else "No character info available."

    emotion_info = ""
    if emotions and "dialogues" in emotions:
        emotion_info = "\n".join(
            f"- Line {d['index']}: {d.get('emotion', '?')} (intensity {d.get('score', '?')}/10)"
            for d in emotions["dialogues"]
        )

    dialogue_text = "\n".join(
        f"[{i}] [{d.get('speaker', '?')}]: {d['text']}" for i, d in enumerate(dialogues[:50])
    )

    lang_name = "English" if target_language == "en" else "Japanese" if target_language == "ja" else target_language

    prompt = f"""Translate this Chinese short drama script to {lang_name}.

IMPORTANT CONTEXT:
Characters:
{char_info}

Emotion per line:
{emotion_info}

GUIDELINES:
- Preserve each character's unique voice and personality in translation
- Match the emotional intensity of each line
- Keep dramatic tension and pacing
- Translate idioms/slang to natural {lang_name} equivalents
- Preserve cultural references where possible, adapt where necessary
- Keep the speaker labels in Chinese

Original dialogue:
{dialogue_text}

Return JSON with format:
{{
  "script": "full formatted translated script as text",
  "summary": "2-3 sentence plot summary in {lang_name}",
  "translations": [
    {{"index": 0, "speaker": "original speaker", "original": "原文", "translated": "translation", "notes": "translation notes if any"}}
  ]
}}"""

    return await call_llm_json(
        prompt,
        system=f"You are an expert Chinese-to-{lang_name} drama translator. You specialize in preserving emotional nuance and character voice.",
        max_tokens=8192,
    )


async def ai_s6_emotion_analysis(dialogues: list[dict], emotions: dict) -> dict | None:
    """S6: Analyze emotion arc and management for the episode."""
    prompt = f"""Analyze the emotional arc of this Chinese short drama episode.

Emotion data per line:
{json.dumps(emotions.get('dialogues', [])[:30], ensure_ascii=False, indent=2) if emotions else 'N/A'}

Identify:
1. arc_type: one of "man_in_a_hole" (starts good, gets bad, recovers), "icarus" (rises then falls), "cinderella" (rises steadily), "rags_to_riches" (dramatic rise), "tragedy" (steady decline), "comedy" (oscillating up)
2. peak_time: approximate timestamp of emotional peak
3. reversals: list of emotional reversal points (where emotion shifts dramatically)
4. average_intensity: average emotional intensity

Return JSON:
{{
  "arc_type": "...",
  "peak_time": "00:MM:SS",
  "reversals": [{{"index": N, "from_emotion": "...", "from_score": N, "to_emotion": "...", "to_score": N, "delta": N}}],
  "average_intensity": N.N
}}"""

    return await call_llm_json(prompt, system="You are a narrative structure analyst for serialized drama.")


async def ai_s7_hook_analysis(dialogues: list[dict], script_data: dict) -> dict | None:
    """S7: Analyze episode-ending hooks for audience retention."""
    last_lines = dialogues[-5:] if len(dialogues) >= 5 else dialogues
    text = "\n".join(f"[{d.get('speaker', '?')}]: {d['text']}" for d in last_lines)

    prompt = f"""Analyze the ending hook of this Chinese short drama episode.

Last few lines of dialogue:
{text}

Translated script summary: {script_data.get('summary', 'N/A') if script_data else 'N/A'}

Evaluate:
1. type: one of "suspense" (unanswered question), "reversal" (plot twist), "emotional" (strong feeling), "threat" (danger), "reveal" (partial truth), "choice" (dilemma)
2. content: describe the hook in Chinese
3. attraction_score: 1-10 how compelling is this hook
4. translation_risk: "LOW", "MEDIUM", or "HIGH" - how much cultural context might be lost
5. risk_reason: if MEDIUM or HIGH, explain why
6. continuity_score: 1-10 how well it connects to the next episode

Return JSON with these fields."""

    return await call_llm_json(prompt, system="You are a short-form video content analyst specializing in audience retention hooks.")


async def ai_qa_review(episode_data: dict) -> dict | None:
    """QA: Quality review of the entire episode processing."""
    prompt = f"""Review the quality of this translated Chinese short drama episode.

Original subtitle lines: {len(episode_data.get('dialogues', []))}
Characters detected: {json.dumps([c.get('name') for c in episode_data.get('characters', [])], ensure_ascii=False)}
Emotion arc type: {episode_data.get('emotion_analysis', {}).get('arc_type', 'N/A')}
Hook type: {episode_data.get('hooks', {}).get('type', 'N/A')}
Translation available: {'yes' if episode_data.get('script') else 'no'}

Score each dimension 1-10:
- asr_quality: subtitle/dialogue extraction quality
- character_consistency: are characters correctly identified and consistent
- emotion_calibration: are emotions accurately labeled and calibrated
- overall_score: overall quality

Also flag any issues as a list of strings.
Set "passed" to true if overall_score >= 7 and no critical issues.

Return JSON:
{{
  "overall_score": N.N,
  "asr_quality": N.N,
  "character_consistency": N.N,
  "emotion_calibration": N.N,
  "issues": ["..."],
  "passed": true/false
}}"""

    return await call_llm_json(prompt, system="You are a quality assurance reviewer for translated drama content.")
