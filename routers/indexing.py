"""
routers/indexing.py
FastAPI router for repository cloning, indexing, and collection status monitoring.
"""

import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException, BackgroundTasks
from core.config import settings
from core.database import set_index_status, get_index_status as db_get_index_status
from indexer import clone_repo, collect_documents, build_index
from schemas.indexing import IndexRequest, IndexResponse

router = APIRouter(prefix="", tags=["Indexing"])

INDEX_STATUS: dict[str, dict] = {}


def sanitize_collection_name(name: str) -> str:
    """Sanitize collection name to be valid for ChromaDB."""
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", name.strip())
    sanitized = re.sub(r"^[^a-zA-Z0-9]+", "", sanitized)
    sanitized = re.sub(r"[^a-zA-Z0-9]+$", "", sanitized)
    if len(sanitized) < 3:
        sanitized = f"repo_{sanitized}"
    return sanitized


def run_indexing_task(name: str, repo_url: str | None = None, local_path: str | None = None):
    """Background task to clone, parse AST, and embed repository documents into ChromaDB."""
    safe_name = sanitize_collection_name(name)
    try:
        msg = f"Cloning and analyzing {repo_url or safe_name}..."
        INDEX_STATUS[name] = {"status": "in_progress", "message": msg}
        INDEX_STATUS[safe_name] = INDEX_STATUS[name]
        set_index_status(name, "in_progress", message=msg)
        set_index_status(safe_name, "in_progress", message=msg)
        print(f"\n[background] Starting index for '{safe_name}'...")

        if local_path:
            repo_path = Path(local_path).resolve()
        else:
            repo_path = clone_repo(repo_url, safe_name)

        msg = f"Parsing code AST and generating chunks for {safe_name}..."
        INDEX_STATUS[name] = {"status": "in_progress", "message": msg}
        INDEX_STATUS[safe_name] = INDEX_STATUS[name]
        set_index_status(name, "in_progress", message=msg)
        set_index_status(safe_name, "in_progress", message=msg)
        documents = collect_documents(repo_path, max_chunks=settings.MAX_CHUNKS_PER_REPO)

        if not documents:
            err = "No indexable code files found (.py, .js, .ts, etc.)."
            INDEX_STATUS[name] = {"status": "failed", "error": err}
            INDEX_STATUS[safe_name] = INDEX_STATUS[name]
            set_index_status(name, "failed", error=err)
            set_index_status(safe_name, "failed", error=err)
            print(f"[background] Error: No indexable code files found for '{safe_name}'.")
            return

        def on_progress(p_msg):
            INDEX_STATUS[name] = {"status": "in_progress", "message": p_msg}
            INDEX_STATUS[safe_name] = INDEX_STATUS[name]
            try:
                set_index_status(name, "in_progress", message=p_msg)
                set_index_status(safe_name, "in_progress", message=p_msg)
            except Exception:
                pass

        msg = f"Embedding {len(documents)} code chunks into vector database..."
        on_progress(msg)
        build_index(documents, collection_name=safe_name, progress_callback=on_progress)

        success_msg = f"Successfully indexed {len(documents)} code chunks for '{safe_name}'!"
        INDEX_STATUS[name] = {"status": "completed", "message": success_msg}
        INDEX_STATUS[safe_name] = INDEX_STATUS[name]
        set_index_status(name, "completed", message=success_msg)
        set_index_status(safe_name, "completed", message=success_msg)
        print(f"[background] Successfully indexed '{safe_name}'!")
    except Exception as e:
        err_msg = str(e)
        INDEX_STATUS[name] = {"status": "failed", "error": err_msg}
        INDEX_STATUS[safe_name] = INDEX_STATUS[name]
        set_index_status(name, "failed", error=err_msg)
        set_index_status(safe_name, "failed", error=err_msg)
        print(f"[background] Indexing failed for '{safe_name}': {e}")


@router.post("/index", response_model=IndexResponse)
def index_repo(req: IndexRequest, background_tasks: BackgroundTasks):
    """Initiate repository cloning and AST indexing in the background."""
    if not req.repo_url and not req.local_path:
        raise HTTPException(status_code=400, detail="Provide either repo_url or local_path")

    if req.local_path:
        repo_path = Path(req.local_path).resolve()
        if not repo_path.exists():
            raise HTTPException(status_code=404, detail=f"Local path not found: {req.local_path}")

    safe_name = sanitize_collection_name(req.name)
    initial_msg = f"Queued: Cloning and analyzing {req.repo_url or safe_name}..."
    INDEX_STATUS[req.name] = {"status": "in_progress", "message": initial_msg}
    INDEX_STATUS[safe_name] = INDEX_STATUS[req.name]
    try:
        set_index_status(req.name, "in_progress", message=initial_msg)
        set_index_status(safe_name, "in_progress", message=initial_msg)
    except Exception:
        pass

    background_tasks.add_task(run_indexing_task, req.name, req.repo_url, req.local_path)

    target = req.repo_url if req.repo_url else req.local_path
    return IndexResponse(
        status="success",
        message=f"Started indexing {target} in the background. This may take a few minutes.",
    )


@router.get("/index/status/{name}")
def get_index_status_endpoint(name: str):
    """Retrieve the current indexing progress/status for a repository."""
    db_status = db_get_index_status(name)
    if db_status.get("status") != "unknown":
        return db_status
    return INDEX_STATUS.get(name, {"status": "unknown"})


@router.get("/collections")
def list_collections():
    """Return all indexed collection names currently stored in ChromaDB."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        return [c.name for c in client.list_collections()]
    except Exception:
        return []
