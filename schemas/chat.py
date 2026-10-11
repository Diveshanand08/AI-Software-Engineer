"""
schemas/chat.py
Pydantic models for chat, explain, agent, bugs, tests, and PR generation requests/responses.
"""

from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    collection: str
    question: str
    model: str = "phi3"
    k: int = 6
    session_id: str | None = None
    provider: str = "ollama"
    user_email: str | None = None


class ExplainRequest(BaseModel):
    collection: str
    target: str
    model: str = "phi3"
    k: int = 6
    provider: str = "ollama"
    user_email: str | None = None


class AnswerResponse(BaseModel):
    answer: str


class BugRequest(BaseModel):
    file_path: str
    model: str = "phi3"


class BugResponse(BaseModel):
    analysis: str


class AgentRequest(BaseModel):
    task: str
    model: str = "phi3"
    max_attempts: int = 3
    session_id: str | None = None
    user_email: str | None = None


class AgentResponse(BaseModel):
    success: bool
    attempts: int
    code: str
    stdout: str
    stderr: str
    error: str | None = None
    session_id: str


class TestGenRequest(BaseModel):
    collection: str
    target: str
    model: str = "phi3"
    max_attempts: int = 3
    session_id: str | None = None
    user_email: str | None = None


class TestGenResponse(BaseModel):
    success: bool
    attempts: int
    code: str
    stdout: str
    stderr: str
    error: str | None = None
    session_id: str


class PRRequest(BaseModel):
    repo_full_name: str
    file_path: str
    code_content: str
    title: str
    description: str = ""


class PRResponse(BaseModel):
    success: bool
    pr_url: str
    branch: str
    message: str
