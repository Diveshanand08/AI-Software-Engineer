"""
db.py
Compatibility facade for the persistence layer.
All logic is centralized in core.database.
"""

from core.database import (
    init_db,
    session_exists,
    create_session,
    get_all_sessions,
    delete_session,
    append_message,
    get_messages,
    set_index_status,
    get_index_status,
)

__all__ = [
    "init_db",
    "session_exists",
    "create_session",
    "get_all_sessions",
    "delete_session",
    "append_message",
    "get_messages",
    "set_index_status",
    "get_index_status",
]
