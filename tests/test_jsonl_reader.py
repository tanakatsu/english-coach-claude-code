import json
from pathlib import Path

import pytest

from english_coach.jsonl_reader import new_user_messages


def _write_jsonl(path: Path, messages: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for m in messages:
            f.write(json.dumps(m, ensure_ascii=False) + "\n")


def _user_msg(
    uuid: str, content: str, ts: str = "2026-04-21T00:00:00Z", is_meta=None
) -> dict:
    obj: dict = {
        "type": "user",
        "uuid": uuid,
        "timestamp": ts,
        "message": {"role": "user", "content": content},
    }
    if is_meta is not None:
        obj["isMeta"] = is_meta
    return obj


# ---------------------------------------------------------------------------
# basic extraction
# ---------------------------------------------------------------------------


def test_returns_all_when_since_uuid_none(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            _user_msg("u1", "hello"),
            _user_msg("u2", "world"),
        ],
    )
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u1", "u2"]


def test_since_uuid_exclusive(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            _user_msg("u1", "first"),
            _user_msg("u2", "second"),
            _user_msg("u3", "third"),
        ],
    )
    result = new_user_messages(path, "u1")
    assert [r["uuid"] for r in result] == ["u2", "u3"]


def test_since_uuid_at_last_returns_empty(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [_user_msg("u1", "only")])
    assert new_user_messages(path, "u1") == []


def test_text_and_ts_fields(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [_user_msg("u1", "hello", ts="2026-04-21T12:00:00Z")])
    result = new_user_messages(path, None)
    assert result[0]["text"] == "hello"
    assert result[0]["ts"] == "2026-04-21T12:00:00Z"


# ---------------------------------------------------------------------------
# exclusion rules
# ---------------------------------------------------------------------------


def test_excludes_is_meta_true(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            _user_msg("u1", "real message"),
            _user_msg("u2", "meta message", is_meta=True),
        ],
    )
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u1"]


def test_excludes_command_name_tag(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            _user_msg("u1", "<command-name>/clear</command-name>"),
            _user_msg("u2", "real"),
        ],
    )
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u2"]


def test_excludes_command_message_tag(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [_user_msg("u1", "<command-message>foo</command-message>")])
    assert new_user_messages(path, None) == []


def test_excludes_local_command_tag(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path, [_user_msg("u1", "<local-command-stdout>ok</local-command-stdout>")]
    )
    assert new_user_messages(path, None) == []


def test_excludes_task_notification(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            _user_msg(
                "u1", "<task-notification> <task-id>abc</task-id> </task-notification>"
            ),
            _user_msg("u2", "real input"),
        ],
    )
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u2"]


def test_excludes_system_reminder(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            _user_msg("u1", "<system-reminder>some system note</system-reminder>"),
            _user_msg("u2", "real input"),
        ],
    )
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u2"]


def test_excludes_shell_command_bang(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            _user_msg("u1", "! rm -rf .venv && uv sync"),
            _user_msg("u2", "real input"),
        ],
    )
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u2"]


def test_excludes_bash_stdout_tag(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            _user_msg(
                "u1",
                "<bash-stdout> M file.py ?? CLAUDE.md</bash-stdout><bash-stderr></bash-stderr>",
            ),
            _user_msg("u2", "real input"),
        ],
    )
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u2"]


def test_excludes_bash_input_tag(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            _user_msg("u1", "<bash-input>git status -s</bash-input>"),
            _user_msg("u2", "real input"),
        ],
    )
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u2"]


def test_excludes_content_as_list(tmp_path):
    path = tmp_path / "s.jsonl"
    msg = {
        "type": "user",
        "uuid": "u1",
        "timestamp": "2026-04-21T00:00:00Z",
        "message": {"role": "user", "content": [{"type": "tool_result"}]},
    }
    _write_jsonl(path, [msg])
    assert new_user_messages(path, None) == []


def test_excludes_empty_content(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [_user_msg("u1", "")])
    assert new_user_messages(path, None) == []


def test_skips_non_user_types(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(
        path,
        [
            {
                "type": "assistant",
                "uuid": "a1",
                "timestamp": "t",
                "message": {"content": "reply"},
            },
            _user_msg("u1", "actual"),
        ],
    )
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u1"]


# ---------------------------------------------------------------------------
# robustness
# ---------------------------------------------------------------------------


def test_missing_file_returns_empty():
    assert new_user_messages("/nonexistent/path.jsonl", None) == []


def test_broken_json_line_skipped(tmp_path):
    path = tmp_path / "s.jsonl"
    with open(path, "w") as f:
        f.write("{broken json\n")
        f.write(json.dumps(_user_msg("u1", "valid")) + "\n")
    result = new_user_messages(path, None)
    assert [r["uuid"] for r in result] == ["u1"]


def test_empty_file_returns_empty(tmp_path):
    path = tmp_path / "s.jsonl"
    path.write_text("")
    assert new_user_messages(path, None) == []


def test_since_uuid_not_in_file_returns_empty(tmp_path):
    path = tmp_path / "s.jsonl"
    _write_jsonl(path, [_user_msg("u1", "hello"), _user_msg("u2", "world")])
    assert new_user_messages(path, "uuid-does-not-exist") == []


def test_since_uuid_on_non_user_line(tmp_path):
    path = tmp_path / "s.jsonl"
    system_line = {
        "type": "system",
        "uuid": "sys-1",
        "timestamp": "2026-04-21T00:00:00Z",
        "content": "some system message",
    }
    _write_jsonl(path, [system_line, _user_msg("u1", "after system")])
    result = new_user_messages(path, "sys-1")
    assert [r["uuid"] for r in result] == ["u1"]
