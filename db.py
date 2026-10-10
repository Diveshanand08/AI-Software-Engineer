"""
db.py
Lightweight SQLite persistence layer for chat sessions and messages.

Tables:
  sessions  — one row per chat session (id, title, created_at)
  messages  — one row per message    (id, session_id, role, content, created_at)

All public functions are thread-safe (SQLite WAL mode + per-call connections).
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "./chat_history.db"))


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL mode for concurrent reads without locking writers
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Call once at startup."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                role       TEXT NOT NULL,
                content    TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_session
                ON messages(session_id);
        """)


# ── Sessions ────────────────────────────────────────────────────────────────

def session_exists(session_id: str) -> bool:
    with _connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return row is not None


def create_session(session_id: str, title: str) -> None:
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, title, created_at) VALUES (?, ?, ?)",
            (session_id, title, now),
        )


def get_all_sessions() -> list[dict]:
    """Return all sessions, newest first."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT id, title, created_at FROM sessions ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_session(session_id: str) -> None:
    with _connect() as conn:
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


# ── Messages ─────────────────────────────────────────────────────────────────

def append_message(session_id: str, role: str, content: str) -> None:
    now = datetime.now().isoformat()
    with _connect() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )


def get_messages(session_id: str) -> list[dict]:
    """Return all messages for a session in chronological order."""
    with _connect() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]
