import json
import logging

import anthropic
from dotenv import load_dotenv

from . import config

load_dotenv()

logger = logging.getLogger(__name__)

try:
    _client: anthropic.Anthropic | None = anthropic.Anthropic()
except Exception:
    _client = None

_SYSTEM_JA = (
    "You are an English writing coach for Japanese software engineers. "
    "The user will give you a Japanese message they wrote to an AI assistant. "
    "Your job is to translate it into natural technical English and explain the key improvement. "
    "Reply ONLY with a JSON object with two keys: "
    '"correction" (the natural English text) and '
    '"explanation" (one short sentence in Japanese explaining the main improvement). '
    "No markdown, no extra keys."
)

_SYSTEM_EN = (
    "You are an English writing coach for software engineers. "
    "The user will give you an English message they wrote to an AI assistant. "
    "If it is already natural, return it unchanged. "
    "Otherwise, rewrite it to be more natural technical English. "
    "Reply ONLY with a JSON object with two keys: "
    '"correction" (the improved or unchanged text) and '
    '"explanation" (one short sentence explaining the improvement, or '
    '"Already natural." if no change was needed). '
    "No markdown, no extra keys."
)


def correct(text: str, language: str) -> dict | None:
    """Call Claude API to correct/translate text.

    Returns {"correction": str, "explanation": str} or None on any failure.
    """
    if _client is None:
        return None
    system = _SYSTEM_JA if language == "ja" else _SYSTEM_EN
    try:
        response = _client.messages.create(
            model=config.MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": text}],
            timeout=8.0,
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = json.loads(raw)
        if "correction" not in data or "explanation" not in data:
            return None
        return {
            "correction": str(data["correction"]),
            "explanation": str(data["explanation"]),
        }
    except Exception as e:
        logger.warning("corrector failed: %s", e)
        return None
