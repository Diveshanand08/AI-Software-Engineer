"""
core/database.py
Thread-safe SQLite persistence layer for sessions, chat history, and indexing tasks.
Uses WAL mode and per-operation connections with busy timeouts to avoid locks.
"""

import sqlite3
from datetime import datetime
from contextlib import contextmanager
from core.config import settings


@contextmanager
def get_connection():
    """Context manager for SQLite connections with WAL mode and error safety."""
    conn = sqlite3.connect(str(settings.DB_PATH), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables if they don't exist and run required migrations."""
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id         TEXT PRIMARY KEY,
                title      TEXT NOT NULL,
                user_email TEXT DEFAULT '',
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

            CREATE TABLE IF NOT EXISTS index_tasks (
                name       TEXT PRIMARY KEY,
                status     TEXT NOT NULL,
                message    TEXT DEFAULT '',
                error      TEXT DEFAULT '',
                updated_at TEXT NOT NULL
            );
        """)

        # Migration: ensure user_email exists in existing databases
        columns = [col[1] for col in conn.execute("PRAGMA table_info(sessions)").fetchall()]
        if "user_email" not in columns:
            conn.execute("ALTER TABLE sessions ADD COLUMN user_email TEXT DEFAULT ''")


# ── Sessions ────────────────────────────────────────────────────────────────

def session_exists(session_id: str) -> bool:
    """Check if a session exists."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return row is not None


def create_session(session_id: str, title: str, user_email: str = "") -> None:
    """Create a new chat session."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO sessions (id, title, user_email, created_at) VALUES (?, ?, ?, ?)",
            (session_id, title, user_email or "", now),
        )


def get_all_sessions(user_email: str | None = None) -> list[dict]:
    """Return sessions filtered by user_email, falling back to all sessions."""
    with get_connection() as conn:
        if user_email and user_email.strip():
            # 1. Exact match (case-insensitive)
            rows = conn.execute(
                "SELECT id, title, created_at, user_email FROM sessions "
                "WHERE LOWER(user_email) = LOWER(?) "
                "ORDER BY created_at DESC",
                (user_email.strip(),),
            ).fetchall()
            if rows:
                return [dict(r) for r in rows]

            # 2. Prefix / username match
            local_user = user_email.strip().split("@")[0]
            clean_prefix = "".join(c for c in local_user if c.isalpha()).lower()
            if clean_prefix and len(clean_prefix) >= 3:
                rows = conn.execute(
                    "SELECT id, title, created_at, user_email FROM sessions "
                    "WHERE LOWER(user_email) LIKE ? "
                    "ORDER BY created_at DESC",
                    (f"%{clean_prefix}%",),
                ).fetchall()
                if rows:
                    return [dict(r) for r in rows]

        # 3. Default fallback
        rows = conn.execute(
            "SELECT id, title, created_at, user_email FROM sessions ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def delete_session(session_id: str) -> None:
    """Delete a session and all its associated messages."""
    with get_connection() as conn:
        conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))


# ── Messages ─────────────────────────────────────────────────────────────────

def append_message(session_id: str, role: str, content: str) -> None:
    """Append a message to a session."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now),
        )


def get_messages(session_id: str) -> list[dict]:
    """Return all messages for a session in chronological order."""
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT role, content, created_at FROM messages "
            "WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ── Index Task Status ────────────────────────────────────────────────────────

def set_index_status(name: str, status: str, message: str = "", error: str = "") -> None:
    """Record or update indexing task state."""
    now = datetime.now().isoformat()
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO index_tasks (name, status, message, error, updated_at)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(name) DO UPDATE SET
                   status = excluded.status,
                   message = excluded.message,
                   error = excluded.error,
                   updated_at = excluded.updated_at""",
            (name, status, message, error, now),
        )


def get_index_status(name: str) -> dict:
    """Retrieve indexing task state."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT status, message, error, updated_at FROM index_tasks WHERE name = ?",
            (name,),
        ).fetchone()
        if not row:
            return {"status": "unknown"}
        return dict(row)
