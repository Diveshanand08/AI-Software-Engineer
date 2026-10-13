"""
core/config.py
Centralized configuration management for the AI Software Engineer assistant.
Loads all environment variables with validation, sensible defaults, and clear documentation.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """Application settings and configuration parameters."""

    # Project metadata
    PROJECT_NAME: str = "AI Code Assistant API"
    VERSION: str = "0.3.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    # Storage Paths
    BASE_DIR: Path = BASE_DIR
    CHROMA_DIR: Path = Path(os.getenv("CHROMA_DIR", str(BASE_DIR / "chroma_db")))
    CLONE_DIR: Path = Path(os.getenv("CLONE_DIR", str(BASE_DIR / "_cloned_repos")))
    DB_PATH: Path = Path(os.getenv("DB_PATH", str(BASE_DIR / "chat_history.db")))

    # LLM Providers & API Keys
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY")
    GROQ_API_KEY: str | None = os.getenv("GROQ_API_KEY")
    GITHUB_TOKEN: str | None = os.getenv("GITHUB_TOKEN")

    # Local Ollama
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    DEFAULT_OLLAMA_MODEL: str = os.getenv("DEFAULT_OLLAMA_MODEL", "phi3")
    EMBED_MODEL: str = os.getenv("EMBED_MODEL", "nomic-embed-text")

    # Server Settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = ["*"]

    # Git Operations
    GIT_CLONE_TIMEOUT_SECONDS: int = int(os.getenv("GIT_CLONE_TIMEOUT_SECONDS", "600"))
    GIT_LOW_SPEED_LIMIT: str = "1000"
    GIT_LOW_SPEED_TIME: str = "600"

    # Indexer limits
    MAX_CHUNKS_PER_REPO: int = int(os.getenv("MAX_CHUNKS_PER_REPO", "100"))
    DEFAULT_RETRIEVAL_K: int = int(os.getenv("DEFAULT_RETRIEVAL_K", "6"))


settings = Settings()
