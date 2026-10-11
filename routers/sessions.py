"""
routers/sessions.py
FastAPI router for session management and chat history.
"""

from fastapi import APIRouter, HTTPException
from core.database import (
    session_exists,
    get_all_sessions,
    get_messages,
    delete_session,
)

router = APIRouter(prefix="", tags=["Sessions"])


@router.get("/sessions")
def list_sessions(user_email: str | None = None):
    """Retrieve chat sessions, optionally filtered by user_email."""
    return get_all_sessions(user_email=user_email)


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Retrieve all messages for a given session ID."""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return get_messages(session_id)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session_endpoint(session_id: str):
    """Delete a chat session and its full message history."""
    if not session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    delete_session(session_id)
