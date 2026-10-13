"""
schemas/indexing.py
Pydantic models for repository indexing and status tracking.
"""

import re
from pydantic import BaseModel, Field, field_validator


class IndexRequest(BaseModel):
    name: str = Field(..., description="Project / collection name for vector database")
    repo_url: str | None = Field(None, description="Public GitHub repository URL")
    local_path: str | None = Field(None, description="Local filesystem path to repository")

    @field_validator("repo_url", mode="before")
    @classmethod
    def sanitize_repo_url(cls, v):
        """
        Extract a clean GitHub URL from whatever the user pastes.
        Handles cases like:
          - '# Index it in your app: https://github.com/pallets/flask'
          - '  https://github.com/tiangolo/fastapi.git  '
        Raises ValueError if no valid GitHub URL is found.
        """
        if v is None:
            return v
        v = str(v).strip()
        # Extract first https://github.com/... URL from the string
        match = re.search(r"https://github\.com/[^\s\"']+", v)
        if match:
            url = match.group(0).rstrip("/")
            # Strip trailing .git if present for consistency
            if url.endswith(".git"):
                url = url[:-4]
            return url
        # If it already looks like a plain github URL (http variant), accept it
        if re.fullmatch(r"https?://github\.com/[^\s\"']+", v):
            return v.rstrip("/")
        raise ValueError(
            f"Invalid GitHub URL: '{v}'. Please provide a valid URL like "
            "https://github.com/owner/repo"
        )


class IndexResponse(BaseModel):
    status: str
    message: str


class IndexStatusResponse(BaseModel):
    status: str
    message: str | None = None
    error: str | None = None
    updated_at: str | None = None
