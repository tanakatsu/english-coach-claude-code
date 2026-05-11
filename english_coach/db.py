import sqlite3
from typing import Optional
from .config import DB_PATH

_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS corrections (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  ts           TEXT    NOT NULL,
  session_id   TEXT    NOT NULL,
  session_date TEXT    NOT NULL,
  language     TEXT    NOT NULL CHECK(language IN ('ja','en')),
  original     TEXT    NOT NULL,
  correction   TEXT    NOT NULL,
  explanation  TEXT,
  pattern_id   INTEGER,
  uuid         TEXT    NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS idx_corrections_session ON corrections(session_id);
CREATE INDEX IF NOT EXISTS idx_corrections_date    ON corrections(session_date);

CREATE TABLE IF NOT EXISTS summaries (
  id         INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id TEXT NOT NULL UNIQUE,
  ts         TEXT NOT NULL,
  body       TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS hook_state (
  session_id          TEXT PRIMARY KEY,
  last_processed_uuid TEXT NOT NULL,
  updated_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patterns (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  signature   TEXT NOT NULL UNIQUE,
  description TEXT,
  first_seen  TEXT NOT NULL,
  last_seen   TEXT NOT NULL,
  occurrences INTEGER NOT NULL DEFAULT 0
);
"""


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)
        try:
            conn.execute(
                "ALTER TABLE corrections ADD COLUMN hidden INTEGER NOT NULL DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_corrections_hidden ON corrections(hidden)"
        )


def insert_correction(
    ts: str,
    session_id: str,
    session_date: str,
    language: str,
    original: str,
    correction: str,
    explanation: Optional[str],
    uuid: str,
) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO corrections
              (ts, session_id, session_date, language, original, correction, explanation, uuid)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(uuid) DO NOTHING
            """,
            (
                ts,
                session_id,
                session_date,
                language,
                original,
                correction,
                explanation,
                uuid,
            ),
        )


def get_latest(n: int = 20) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM corrections WHERE hidden = 0 ORDER BY id DESC LIMIT ?", (n,)
        ).fetchall()
    return [dict(r) for r in rows]


def get_history(
    session_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    with _connect() as conn:
        if session_id:
            rows = conn.execute(
                "SELECT * FROM corrections WHERE session_id=? AND hidden = 0 ORDER BY id DESC LIMIT ? OFFSET ?",
                (session_id, limit, offset),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM corrections WHERE hidden = 0 ORDER BY id DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
    return [dict(r) for r in rows]


def hide_correction(correction_id: int) -> None:
    with _connect() as conn:
        conn.execute("UPDATE corrections SET hidden = 1 WHERE id = ?", (correction_id,))


def insert_summary(session_id: str, ts: str, body: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO summaries (session_id, ts, body)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET ts=excluded.ts, body=excluded.body
            """,
            (session_id, ts, body),
        )


def get_last_uuid(session_id: str) -> Optional[str]:
    with _connect() as conn:
        row = conn.execute(
            "SELECT last_processed_uuid FROM hook_state WHERE session_id=?",
            (session_id,),
        ).fetchone()
    return row["last_processed_uuid"] if row else None


def set_last_uuid(session_id: str, uuid: str, updated_at: str) -> None:
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO hook_state (session_id, last_processed_uuid, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
              last_processed_uuid=excluded.last_processed_uuid,
              updated_at=excluded.updated_at
            """,
            (session_id, uuid, updated_at),
        )
