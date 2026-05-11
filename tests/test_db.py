import sqlite3

import pytest

import english_coach.db as db_module
from english_coach.db import (
    get_history,
    get_last_uuid,
    get_latest,
    hide_correction,
    init_db,
    insert_correction,
    set_last_uuid,
)

_TS = "2026-04-21T00:00:00Z"
_DATE = "2026-04-21"


@pytest.fixture(autouse=True)
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    init_db()


def _insert(uuid="uuid-1", session_id="sess-1", language="ja"):
    insert_correction(
        _TS, session_id, _DATE, language, "original", "correction", "explanation", uuid
    )


# ---------------------------------------------------------------------------
# init_db
# ---------------------------------------------------------------------------


def test_init_db_creates_tables(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "fresh.db")
    init_db()
    with sqlite3.connect(tmp_path / "fresh.db") as conn:
        tables = {
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert {"corrections", "hook_state", "summaries", "patterns"} <= tables


def test_init_db_idempotent():
    _insert()
    init_db()  # second call on same DB — data must survive
    assert len(get_latest()) == 1


# ---------------------------------------------------------------------------
# insert_correction / get_latest
# ---------------------------------------------------------------------------


def test_insert_and_get_latest():
    _insert()
    rows = get_latest()
    assert len(rows) == 1
    assert rows[0]["uuid"] == "uuid-1"
    assert rows[0]["language"] == "ja"


def test_insert_explanation_none():
    insert_correction(_TS, "sess-1", _DATE, "ja", "orig", "corr", None, "uuid-none")
    rows = get_latest()
    assert rows[0]["explanation"] is None


def test_insert_invalid_language_raises():
    import sqlite3 as _sqlite3

    with pytest.raises(_sqlite3.IntegrityError):
        insert_correction(_TS, "sess-1", _DATE, "zh", "orig", "corr", None, "uuid-zh")


def test_insert_idempotent():
    _insert()
    _insert()  # same uuid — should be ignored
    assert len(get_latest()) == 1


def test_get_latest_order_and_limit():
    for i in range(5):
        _insert(uuid=f"uuid-{i}")
    rows = get_latest(n=3)
    assert len(rows) == 3
    # DESC by id: last inserted comes first
    assert rows[0]["uuid"] == "uuid-4"


# ---------------------------------------------------------------------------
# get_history
# ---------------------------------------------------------------------------


def test_get_history_empty_session_id_falls_through():
    _insert(uuid="a", session_id="sess-A")
    _insert(uuid="b", session_id="sess-B")
    rows = get_history(session_id="")  # "" is falsy — returns all rows
    assert len(rows) == 2


def test_get_history_session_filter():
    _insert(uuid="a", session_id="sess-A")
    _insert(uuid="b", session_id="sess-B")
    rows = get_history(session_id="sess-A")
    assert len(rows) == 1
    assert rows[0]["uuid"] == "a"


def test_get_history_pagination():
    for i in range(5):
        _insert(uuid=f"uuid-{i}")
    page1 = get_history(limit=2, offset=0)
    page2 = get_history(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {r["uuid"] for r in page1}.isdisjoint({r["uuid"] for r in page2})


# ---------------------------------------------------------------------------
# hook_state
# ---------------------------------------------------------------------------


def test_get_last_uuid_returns_none_initially():
    assert get_last_uuid("sess-new") is None


def test_set_and_get_last_uuid():
    set_last_uuid("sess-1", "uuid-42", _TS)
    assert get_last_uuid("sess-1") == "uuid-42"


def test_set_last_uuid_upsert():
    set_last_uuid("sess-1", "uuid-1", _TS)
    set_last_uuid("sess-1", "uuid-2", _TS)
    assert get_last_uuid("sess-1") == "uuid-2"


# ---------------------------------------------------------------------------
# hidden column migration
# ---------------------------------------------------------------------------


def test_hidden_column_migration_idempotent():
    init_db()  # second call on same DB — must not raise OperationalError


def test_hide_correction():
    _insert()
    row_id = get_latest()[0]["id"]
    hide_correction(row_id)
    assert get_latest() == []


def test_latest_excludes_hidden():
    _insert(uuid="uuid-a")
    _insert(uuid="uuid-b")
    row_id = get_latest()[0]["id"]  # most recent
    hide_correction(row_id)
    rows = get_latest()
    assert len(rows) == 1
    assert rows[0]["uuid"] == "uuid-a"


def test_history_excludes_hidden():
    _insert(uuid="uuid-a", session_id="sess-X")
    _insert(uuid="uuid-b", session_id="sess-X")
    row_id = get_latest()[0]["id"]
    hide_correction(row_id)
    # without session_id filter
    assert len(get_history()) == 1
    # with session_id filter
    assert len(get_history(session_id="sess-X")) == 1
