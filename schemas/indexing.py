"""
schemas/indexing.py
Pydantic models for repository indexing and status tracking.
"""

from pydantic import BaseModel, Field


class IndexRequest(BaseModel):
    name: str = Field(..., description="Project / collection name for vector database")
    repo_url: str | None = Field(None, description="Public GitHub repository URL")
    local_path: str | None = Field(None, description="Local filesystem path to repository")


class IndexResponse(BaseModel):
    status: str
    message: str


class IndexStatusResponse(BaseModel):
    status: str
    message: str | None = None
    error: str | None = None
    updated_at: str | None = None
