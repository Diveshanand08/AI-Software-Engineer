"""
core/exceptions.py
Custom domain exceptions for clean and consistent error handling throughout the application.
"""

class CodeAssistantException(Exception):
    """Base exception for all application errors."""
    def __init__(self, message: str, status_code: int = 500):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class CollectionNotFoundError(CodeAssistantException):
    """Raised when an indexed collection does not exist in ChromaDB."""
    def __init__(self, collection_name: str):
        super().__init__(
            f"Collection '{collection_name}' not found or empty. Please index the repository first.",
            status_code=404,
        )


class RepositoryCloneError(CodeAssistantException):
    """Raised when cloning a git repository fails."""
    def __init__(self, repo_url: str, detail: str):
        super().__init__(
            f"Failed to clone repository '{repo_url}': {detail}",
            status_code=400,
        )


class ProviderUnavailableError(CodeAssistantException):
    """Raised when an LLM provider is requested but not configured or reachable."""
    def __init__(self, provider: str, detail: str):
        super().__init__(
            f"LLM provider '{provider}' is currently unavailable: {detail}",
            status_code=503,
        )


class SessionNotFoundError(CodeAssistantException):
    """Raised when a chat session ID does not exist."""
    def __init__(self, session_id: str):
        super().__init__(
            f"Session '{session_id}' not found.",
            status_code=404,
        )
