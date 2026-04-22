import json
from unittest.mock import patch

import pytest

from english_coach import hook


def test_run_skips_empty_session_id():
    """No processing when session_id is missing."""
    with patch("english_coach.hook.db") as mock_db:
        hook.run({})
        mock_db.get_last_uuid.assert_not_called()


def test_run_skips_missing_transcript():
    with patch("english_coach.hook.db") as mock_db:
        hook.run({"session_id": "s1"})
        mock_db.get_last_uuid.assert_not_called()


def test_run_no_new_messages():
    with (
        patch("english_coach.hook.db") as mock_db,
        patch("english_coach.hook.new_user_messages", return_value=[]),
    ):
        mock_db.get_last_uuid.return_value = None
        hook.run({"session_id": "s1", "transcript_path": "/fake/path.jsonl"})
        mock_db.set_last_uuid.assert_not_called()


def test_run_skips_undetermined_language():
    msgs = [{"uuid": "u1", "text": "123!@#", "ts": "2026-01-01T00:00:00Z"}]
    with (
        patch("english_coach.hook.db") as mock_db,
        patch("english_coach.hook.new_user_messages", return_value=msgs),
        patch("english_coach.hook.detect", return_value=None),
        patch("english_coach.hook.correct") as mock_correct,
        patch("english_coach.hook.httpx.post") as mock_post,
    ):
        mock_db.get_last_uuid.return_value = None
        hook.run({"session_id": "s1", "transcript_path": "/fake/path.jsonl"})
        mock_correct.assert_not_called()
        mock_post.assert_not_called()
        args = mock_db.set_last_uuid.call_args[0]
        assert args[0] == "s1"
        assert args[1] == "u1"
        assert isinstance(args[2], str)


def test_run_posts_correction_and_updates_uuid():
    msgs = [{"uuid": "u1", "text": "サーバーを起動して", "ts": "2026-01-01T00:00:00Z"}]
    correction = {"correction": "Please start the server.", "explanation": "翻訳"}
    with (
        patch("english_coach.hook.db") as mock_db,
        patch("english_coach.hook.new_user_messages", return_value=msgs),
        patch("english_coach.hook.detect", return_value="ja"),
        patch("english_coach.hook.correct", return_value=correction),
        patch("english_coach.hook.httpx.post") as mock_post,
    ):
        mock_db.get_last_uuid.return_value = None
        hook.run({"session_id": "s1", "transcript_path": "/fake/path.jsonl"})

        mock_post.assert_called_once()
        posted = mock_post.call_args.kwargs["json"]
        assert posted["uuid"] == "u1"
        assert posted["language"] == "ja"
        assert posted["original"] == "サーバーを起動して"
        assert posted["correction"] == "Please start the server."
        assert posted["explanation"] == "翻訳"
        assert posted["session_id"] == "s1"
        mock_db.set_last_uuid.assert_called_once()


def test_run_skips_when_corrector_returns_none():
    """When correct() fails, no POST is made but uuid is still advanced."""
    msgs = [{"uuid": "u1", "text": "サーバーを起動して", "ts": "2026-01-01T00:00:00Z"}]
    with (
        patch("english_coach.hook.db") as mock_db,
        patch("english_coach.hook.new_user_messages", return_value=msgs),
        patch("english_coach.hook.detect", return_value="ja"),
        patch("english_coach.hook.correct", return_value=None),
        patch("english_coach.hook.httpx.post") as mock_post,
    ):
        mock_db.get_last_uuid.return_value = None
        hook.run({"session_id": "s1", "transcript_path": "/fake/path.jsonl"})
        mock_post.assert_not_called()
        mock_db.set_last_uuid.assert_called_once()
        assert mock_db.set_last_uuid.call_args[0][1] == "u1"


def test_run_handles_post_failure_gracefully():
    """POST failure should not raise — hook must exit 0."""
    msgs = [{"uuid": "u1", "text": "hello", "ts": "2026-01-01T00:00:00Z"}]
    correction = {"correction": "Hello.", "explanation": "Already natural."}
    with (
        patch("english_coach.hook.db") as mock_db,
        patch("english_coach.hook.new_user_messages", return_value=msgs),
        patch("english_coach.hook.detect", return_value="en"),
        patch("english_coach.hook.correct", return_value=correction),
        patch(
            "english_coach.hook.httpx.post", side_effect=Exception("connection refused")
        ),
    ):
        mock_db.get_last_uuid.return_value = None
        hook.run({"session_id": "s1", "transcript_path": "/fake/path.jsonl"})
        mock_db.set_last_uuid.assert_called_once()


def test_main_exits_zero_on_invalid_json(monkeypatch):
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO("not json"))
    with pytest.raises(SystemExit) as exc_info:
        hook.main()
    assert exc_info.value.code == 0


def test_main_exits_zero_on_valid_payload(monkeypatch):
    payload = json.dumps({"session_id": "s1", "transcript_path": "/fake.jsonl"})
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(payload))
    with (
        patch("english_coach.hook.new_user_messages", return_value=[]),
        patch("english_coach.hook.db"),
        pytest.raises(SystemExit) as exc_info,
    ):
        hook.main()
    assert exc_info.value.code == 0
