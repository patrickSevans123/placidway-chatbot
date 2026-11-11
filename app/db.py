"""SQLite storage for chat history, unanswered questions and leads.

One file, no server. The unanswered table is the content-gap report the brief
asks for: every question the bot could not answer, with the intent and the
retrieval confidence, so the team can see which page is missing.
"""

from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL,
    last_seen   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    intent      TEXT,
    grounded    INTEGER,
    confidence  REAL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);

CREATE TABLE IF NOT EXISTS unanswered (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT,
    question    TEXT NOT NULL,
    intent      TEXT,
    confidence  REAL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS leads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT,
    name        TEXT NOT NULL,
    email       TEXT NOT NULL,
    message     TEXT,
    created_at  TEXT NOT NULL
);
"""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


@contextmanager
def connect():
    path: Path = settings.db_path
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def touch_session(session_id: str) -> None:
    now = _now()
    with connect() as conn:
        conn.execute(
            "INSERT INTO sessions (id, created_at, last_seen) VALUES (?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET last_seen = excluded.last_seen",
            (session_id, now, now),
        )


def add_message(
    session_id: str,
    role: str,
    content: str,
    *,
    intent: str | None = None,
    grounded: bool | None = None,
    confidence: float | None = None,
) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, intent, grounded, confidence, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                role,
                content,
                intent,
                None if grounded is None else int(grounded),
                confidence,
                _now(),
            ),
        )


def history(session_id: str, limit: int = 12) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def log_unanswered(session_id: str, question: str, intent: str, confidence: float) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO unanswered (session_id, question, intent, confidence, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (session_id, question, intent, confidence, _now()),
        )


def unanswered(limit: int = 100) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT question, intent, confidence, created_at FROM unanswered ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def add_lead(session_id: str, name: str, email: str, message: str | None) -> None:
    with connect() as conn:
        conn.execute(
            "INSERT INTO leads (session_id, name, email, message, created_at) VALUES (?, ?, ?, ?, ?)",
            (session_id, name, email, message, _now()),
        )


def stats() -> dict:
    with connect() as conn:
        sessions = conn.execute("SELECT COUNT(*) AS n FROM sessions").fetchone()["n"]
        messages = conn.execute("SELECT COUNT(*) AS n FROM messages").fetchone()["n"]
        gaps = conn.execute("SELECT COUNT(*) AS n FROM unanswered").fetchone()["n"]
        leads = conn.execute("SELECT COUNT(*) AS n FROM leads").fetchone()["n"]
    return {"sessions": sessions, "messages": messages, "unanswered": gaps, "leads": leads}
