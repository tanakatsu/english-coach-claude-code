import json
from pathlib import Path

_COMMAND_TAGS = (
    "<command-name>",
    "<command-message>",
    "<command-args>",
    "<local-command-",
)


def _is_excluded(content: str) -> bool:
    return any(tag in content for tag in _COMMAND_TAGS)


def new_user_messages(
    session_jsonl_path: str | Path,
    since_uuid: str | None,
) -> list[dict]:
    """Return user messages after since_uuid (exclusive).

    Each item: {"uuid": str, "text": str, "ts": str}
    """
    path = Path(session_jsonl_path)
    if not path.exists():
        return []

    lines: list[dict] = []
    past_since = since_uuid is None

    with open(path, encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue

            uuid = obj.get("uuid")

            if not past_since:
                if uuid == since_uuid:
                    past_since = True
                continue

            if obj.get("type") != "user":
                continue
            if obj.get("isMeta"):
                continue

            msg = obj.get("message", {})
            if not isinstance(msg, dict):
                continue

            content = msg.get("content", "")
            if isinstance(content, list):
                continue
            if not isinstance(content, str) or not content.strip():
                continue
            if _is_excluded(content):
                continue

            ts = obj.get("timestamp", "")
            if uuid:
                lines.append({"uuid": uuid, "text": content, "ts": ts})

    return lines
