import json
from unittest.mock import MagicMock, patch

import pytest

from english_coach.corrector import correct


def _make_response(text: str) -> MagicMock:
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


@patch("english_coach.corrector._client")
def test_correct_ja(mock_client):
    payload = {
        "correction": "Please start the server.",
        "explanation": "日本語を自然な技術英語に翻訳しました。",
    }
    mock_client.messages.create.return_value = _make_response(json.dumps(payload))

    result = correct("サーバーを起動してください", "ja")

    assert result == payload
    call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["system"].startswith(
        "You are an English writing coach for Japanese"
    )


@patch("english_coach.corrector._client")
def test_correct_en(mock_client):
    payload = {
        "correction": "Could you start the server?",
        "explanation": "More polite phrasing.",
    }
    mock_client.messages.create.return_value = _make_response(json.dumps(payload))

    result = correct("can you start server", "en")

    assert result == payload
    call_kwargs = mock_client.messages.create.call_args
    assert "already natural" in call_kwargs.kwargs["system"].lower()


@patch("english_coach.corrector._client")
def test_correct_returns_none_on_api_error(mock_client):
    mock_client.messages.create.side_effect = Exception("API error")

    result = correct("test", "en")

    assert result is None


@patch("english_coach.corrector._client")
def test_correct_returns_none_on_invalid_json(mock_client):
    mock_client.messages.create.return_value = _make_response("not json at all")

    result = correct("test", "en")

    assert result is None


@patch("english_coach.corrector._client")
def test_correct_returns_none_on_missing_keys(mock_client):
    mock_client.messages.create.return_value = _make_response(
        json.dumps({"only_one": "key"})
    )

    result = correct("test", "ja")

    assert result is None


@patch("english_coach.corrector._client")
def test_correct_returns_none_when_client_is_none(mock_client):
    mock_client.__bool__ = lambda self: False
    with patch("english_coach.corrector._client", None):
        result = correct("test", "en")
    assert result is None


@patch("english_coach.corrector._client")
def test_correct_handles_markdown_fenced_json(mock_client):
    payload = {
        "correction": "Please start the server.",
        "explanation": "Clearer phrasing.",
    }
    fenced = f"```json\n{json.dumps(payload)}\n```"
    mock_client.messages.create.return_value = _make_response(fenced)

    result = correct("start the server please", "en")

    assert result == payload


@patch("english_coach.corrector._client")
def test_correct_passes_timeout(mock_client):
    payload = {"correction": "Hello.", "explanation": "Fine."}
    mock_client.messages.create.return_value = _make_response(json.dumps(payload))

    correct("hello", "en")

    call_kwargs = mock_client.messages.create.call_args
    assert call_kwargs.kwargs["timeout"] == 8.0
