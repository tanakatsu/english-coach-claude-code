import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone

import httpx

from . import config, db
from .corrector import correct
from .jsonl_reader import new_user_messages
from .language import detect

_LOG_PATH = config.DB_PATH.parent / "hook.log"
_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

_logger = logging.getLogger(__name__)
_handler = logging.FileHandler(_LOG_PATH)
_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(logging.ERROR)


def _server_url() -> str:
    return f"http://{config.SERVER_HOST}:{config.SERVER_PORT}/api/feedback"


def run(payload: dict) -> None:
    session_id = payload.get("session_id", "")
    transcript_path = payload.get("transcript_path", "")

    if not session_id or not transcript_path:
        return

    last_uuid = db.get_last_uuid(session_id)
    messages = new_user_messages(transcript_path, last_uuid)
    if not messages:
        return

    latest_uuid = None
    for msg in messages:
        lang = detect(msg["text"])
        if lang is None:
            latest_uuid = msg["uuid"]
            continue

        result = correct(msg["text"], lang)
        if result is None:
            latest_uuid = msg["uuid"]
            continue

        ts = msg["ts"] or datetime.now(timezone.utc).isoformat()
        session_date = (
            ts[:10]
            if len(ts) >= 10
            else datetime.now(timezone.utc).strftime("%Y-%m-%d")
        )

        payload_data = {
            "ts": ts,
            "session_id": session_id,
            "session_date": session_date,
            "language": lang,
            "original": msg["text"],
            "correction": result["correction"],
            "explanation": result["explanation"],
            "uuid": msg["uuid"],
        }

        try:
            response = httpx.post(_server_url(), json=payload_data, timeout=5.0)
            response.raise_for_status()
        except Exception as e:
            _logger.error("POST /api/feedback failed: %s", e)
            latest_uuid = msg["uuid"]
            continue

        latest_uuid = msg["uuid"]

    if latest_uuid:
        updated_at = datetime.now(timezone.utc).isoformat()
        db.set_last_uuid(session_id, latest_uuid, updated_at)


def main() -> None:
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
        run(payload)
    except Exception as e:
        _logger.error("hook error: %s", e)
    sys.exit(0)


if __name__ == "__main__":
    main()
