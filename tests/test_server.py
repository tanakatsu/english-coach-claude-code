import pytest
from fastapi.testclient import TestClient

import english_coach.db as db_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    # Import server after monkeypatching so lifespan uses the patched path
    import importlib
    import server

    importlib.reload(server)
    with TestClient(server.app) as c:
        yield c


def test_latest_empty(client):
    resp = client.get("/api/latest")
    assert resp.status_code == 200
    assert resp.json() == []


def test_post_feedback_and_latest(client):
    payload = {
        "ts": "2026-04-22T10:00:00Z",
        "session_id": "sess-1",
        "session_date": "2026-04-22",
        "language": "ja",
        "original": "サーバーを起動して",
        "correction": "Please start the server.",
        "explanation": "More natural phrasing.",
        "uuid": "uuid-abc-001",
    }
    resp = client.post("/api/feedback", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    resp = client.get("/api/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["original"] == "サーバーを起動して"
    assert data[0]["language"] == "ja"


def test_post_feedback_idempotent(client):
    payload = {
        "ts": "2026-04-22T10:00:00Z",
        "session_id": "sess-1",
        "session_date": "2026-04-22",
        "language": "en",
        "original": "start server",
        "correction": "Please start the server.",
        "explanation": None,
        "uuid": "uuid-idem-001",
    }
    client.post("/api/feedback", json=payload)
    client.post("/api/feedback", json=payload)  # duplicate → ignored
    resp = client.get("/api/latest")
    assert len(resp.json()) == 1


def test_post_summary(client):
    payload = {
        "session_id": "sess-1",
        "ts": "2026-04-22T10:00:00Z",
        "body": "## Summary",
    }
    resp = client.post("/api/summary", json=payload)
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_history_filter_by_session(client):
    for i, lang in enumerate(["ja", "en"]):
        client.post(
            "/api/feedback",
            json={
                "ts": f"2026-04-22T10:0{i}:00Z",
                "session_id": f"sess-{i}",
                "session_date": "2026-04-22",
                "language": lang,
                "original": f"msg {i}",
                "correction": f"corrected {i}",
                "explanation": None,
                "uuid": f"uuid-hist-{i:03d}",
            },
        )

    resp = client.get("/api/history?session_id=sess-0")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["session_id"] == "sess-0"


def test_index_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]
    body = resp.text
    assert "English Coach" in body
    assert "/api/latest" in body
    assert "filter-bar" in body


def test_feedback_invalid_language(client):
    payload = {
        "ts": "2026-04-22T10:00:00Z",
        "session_id": "sess-1",
        "session_date": "2026-04-22",
        "language": "zh",
        "original": "你好",
        "correction": "Hello",
        "explanation": None,
        "uuid": "uuid-lang-001",
    }
    resp = client.post("/api/feedback", json=payload)
    assert resp.status_code == 422


def test_latest_limit_too_large(client):
    resp = client.get("/api/latest?limit=999999")
    assert resp.status_code == 422


def _post_feedback(client, uuid="uuid-hide-001"):
    return client.post(
        "/api/feedback",
        json={
            "ts": "2026-04-22T10:00:00Z",
            "session_id": "sess-1",
            "session_date": "2026-04-22",
            "language": "ja",
            "original": "original",
            "correction": "corrected",
            "explanation": None,
            "uuid": uuid,
        },
    )


def test_hide_correction_endpoint(client):
    _post_feedback(client)
    correction_id = client.get("/api/latest").json()[0]["id"]
    resp = client.patch(f"/api/corrections/{correction_id}/hidden")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}


def test_hide_removes_from_latest(client):
    _post_feedback(client)
    correction_id = client.get("/api/latest").json()[0]["id"]
    client.patch(f"/api/corrections/{correction_id}/hidden")
    assert client.get("/api/latest").json() == []


def test_index_html_new_filter_buttons(client):
    body = client.get("/").text
    assert "This Week" in body
    assert "This Month" in body
