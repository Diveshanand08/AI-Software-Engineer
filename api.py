"""
api.py
FastAPI backend exposing the code assistant's core features as HTTP endpoints:
  POST /index    - index a repo (local path or git URL)
  POST /ask      - free-form Q&A about an indexed repo (streaming)
  POST /explain  - structured explanation of a function/class (streaming)
  POST /bugs     - run bug detection on a specific file

Usage:
    uvicorn api:app --reload --port 8000

Then visit http://localhost:8000/docs for interactive Swagger UI.
"""

import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

from db import init_db, session_exists, create_session, get_all_sessions, get_messages, append_message, delete_session
from indexer import clone_repo, collect_documents, build_index
from chat import ask as chat_ask, explain as chat_explain
from llm import available_providers
from bug_finder import analyze_file
from chat import ask_stream, explain_stream

app = FastAPI(
    title="AI Code Assistant API",
    description="RAG-based code assistant: index repos, chat, explain functions, find bugs.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only - restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    """Initialize the SQLite database on server start."""
    init_db()
    print("[db] SQLite chat history database ready.")


# ---- request/response models ----
class IndexRequest(BaseModel):
    name: str
    repo_url: str | None = None
    local_path: str | None = None

class IndexResponse(BaseModel):
    status: str
    message: str

class AskRequest(BaseModel):
    collection: str
    question: str
    model: str = "phi3"
    k: int = 4
    session_id: str | None = None
    provider: str = "ollama"

class ExplainRequest(BaseModel):
    collection: str
    target: str
    model: str = "phi3"
    k: int = 4
    provider: str = "ollama"

class AnswerResponse(BaseModel):
    answer: str

class BugRequest(BaseModel):
    file_path: str
    model: str = "phi3"

class BugResponse(BaseModel):
    analysis: str


# ---- background tasks ----
def run_indexing_task(name: str, repo_url: str | None = None, local_path: str | None = None):
    try:
        print(f"\n[background] Starting index for '{name}'...")
        if local_path:
            repo_path = Path(local_path).resolve()
        else:
            repo_path = clone_repo(repo_url, name)

        documents = collect_documents(repo_path)
        if not documents:
            print(f"[background] Error: No indexable code files found for '{name}'.")
            return

        build_index(documents, collection_name=name)
        print(f"[background] Successfully indexed '{name}'!")

        # Clean up temporary clone if it was cloned from a remote git URL
        if repo_url and repo_path.exists():
            shutil.rmtree(repo_path, ignore_errors=True)
            print(f"[background] Cleaned up temporary clone at {repo_path}")
    except Exception as e:
        print(f"[background] Indexing failed for '{name}': {e}")


# ---- endpoints ----
@app.get("/")
def root():
    return {"status": "ok", "service": "AI Code Assistant API"}

@app.get("/providers")
def providers():
    return available_providers()


# ── Session endpoints ──────────────────────────────────────────────────────

@app.get("/sessions")
def list_sessions():
    """Returns metadata for all sessions (persistent across restarts)."""
    return get_all_sessions()


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Returns the full message history for a specific session."""
    if not session_exists(session_id):
        raise HTTPException(404, "Session not found")
    return get_messages(session_id)


@app.delete("/sessions/{session_id}", status_code=204)
def delete_session_endpoint(session_id: str):
    """Deletes a session and all its messages."""
    if not session_exists(session_id):
        raise HTTPException(404, "Session not found")
    delete_session(session_id)


# ── Core endpoints ─────────────────────────────────────────────────────────

@app.post("/index", response_model=IndexResponse)
def index_repo(req: IndexRequest, background_tasks: BackgroundTasks):
    if not req.repo_url and not req.local_path:
        raise HTTPException(400, "Provide either repo_url or local_path")

    if req.local_path:
        repo_path = Path(req.local_path).resolve()
        if not repo_path.exists():
            raise HTTPException(404, f"Local path not found: {req.local_path}")

    background_tasks.add_task(run_indexing_task, req.name, req.repo_url, req.local_path)

    target = req.repo_url if req.repo_url else req.local_path
    return IndexResponse(
        status="success",
        message=f"Started indexing {target} in the background. This may take a few minutes."
    )


@app.post("/ask")
def ask_endpoint(req: AskRequest):
    # 1. Resolve or create session in SQLite
    session_id = req.session_id
    if not session_id or not session_exists(session_id):
        session_id = str(uuid.uuid4())
        title = req.question[:30] + "..." if len(req.question) > 30 else req.question
        create_session(session_id, title)

    # 2. Persist the user's question immediately
    append_message(session_id, "user", req.question)

    # 3. Stream AI response, persist on completion
    def stream_and_save():
        yield f"__SESSION_ID__:{session_id}\n\n"

        full_ai_response = ""
        original_stream = ask_stream(
            req.collection, req.question, model=req.model, k=req.k, provider=req.provider
        )

        try:
            for chunk in original_stream:
                full_ai_response += chunk
                yield chunk
        except Exception as e:
            err = f"\n\n**Error ({req.provider}):** {e}"
            full_ai_response += err
            yield err
        finally:
            if full_ai_response:
                append_message(session_id, "ai", full_ai_response)

    return StreamingResponse(stream_and_save(), media_type="text/plain")


@app.post("/explain")
def explain_endpoint(req: ExplainRequest):
    return StreamingResponse(
        explain_stream(req.collection, req.target, model=req.model, k=req.k, provider=req.provider),
        media_type="text/plain"
    )


@app.post("/bugs", response_model=BugResponse)
def bugs_endpoint(req: BugRequest):
    path = Path(req.file_path)
    if not path.exists():
        raise HTTPException(404, f"File not found: {req.file_path}")
    result = analyze_file(str(path), model=req.model)
    return BugResponse(analysis=result)