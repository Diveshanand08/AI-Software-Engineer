"""
schemas/sessions.py
Pydantic models for chat session history.
"""

from pydantic import BaseModel


class SessionItem(BaseModel):
    id: str
    title: str
    user_email: str | None = ""
    created_at: str


class MessageItem(BaseModel):
    role: str
    content: str
    created_at: str
