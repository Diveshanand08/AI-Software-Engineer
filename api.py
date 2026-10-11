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

import os
import re
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

from db import (
    init_db,
    session_exists,
    create_session,
    get_all_sessions,
    get_messages,
    append_message,
    delete_session,
    set_index_status,
    get_index_status as db_get_index_status,
)
from indexer import clone_repo, collect_documents, build_index
from chat import ask as chat_ask, explain as chat_explain
from llm import available_providers
from bug_finder import analyze_file
from chat import ask_stream, explain_stream
from Code_agent import run_agent
from test_generator import generate_tests_for_target
from pr_generator import create_fix_pr

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
    user_email: str | None = None

class ExplainRequest(BaseModel):
    collection: str
    target: str
    model: str = "phi3"
    k: int = 4
    provider: str = "ollama"
    user_email: str | None = None

class AnswerResponse(BaseModel):
    answer: str

class BugRequest(BaseModel):
    file_path: str
    model: str = "phi3"

class BugResponse(BaseModel):
    analysis: str


# ---- background tasks & status tracking ----
INDEX_STATUS: dict[str, dict] = {}

def sanitize_collection_name(name: str) -> str:
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", name.strip())
    sanitized = re.sub(r"^[^a-zA-Z0-9]+", "", sanitized)
    sanitized = re.sub(r"[^a-zA-Z0-9]+$", "", sanitized)
    if len(sanitized) < 3:
        sanitized = f"repo_{sanitized}"
    return sanitized

def run_indexing_task(name: str, repo_url: str | None = None, local_path: str | None = None):
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
        documents = collect_documents(repo_path)
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


# ---- endpoints ----
@app.get("/")
def root():
    return {"status": "ok", "service": "AI Code Assistant API"}

@app.get("/providers")
def providers():
    return available_providers()

@app.get("/collections")
def list_collections():
    """Return all indexed collection names currently stored in ChromaDB."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=os.getenv("CHROMA_DIR", "./chroma_db"))
        return [c.name for c in client.list_collections()]
    except Exception:
        return []

@app.get("/index/status/{name}")
def get_index_status_endpoint(name: str):
    """Return the current indexing progress/status for a repository."""
    db_status = db_get_index_status(name)
    if db_status.get("status") != "unknown":
        return db_status
    return INDEX_STATUS.get(name, {"status": "unknown"})


# ── Session endpoints ──────────────────────────────────────────────────────

@app.get("/sessions")
def list_sessions(user_email: str | None = None):
    """Returns metadata for sessions filtered by user_email."""
    return get_all_sessions(user_email=user_email)


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
        message=f"Started indexing {target} in the background. This may take a few minutes."
    )


@app.post("/ask")
def ask_endpoint(req: AskRequest):
    # 1. Resolve or create session in SQLite
    session_id = req.session_id
    if not session_id or not session_exists(session_id):
        session_id = str(uuid.uuid4())
        title = req.question[:30] + "..." if len(req.question) > 30 else req.question
        create_session(session_id, title, user_email=req.user_email or "")

    # 2. Persist the user's question immediately
    append_message(session_id, "user", req.question)

    # 3. Stream AI response, persist on completion
    def stream_and_save():
        yield f"__SESSION_ID__:{session_id}\n\n"

        full_ai_response = ""
        safe_coll = sanitize_collection_name(req.collection)
        original_stream = ask_stream(
            safe_coll, req.question, model=req.model, k=req.k, provider=req.provider
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
    safe_coll = sanitize_collection_name(req.collection)
    return StreamingResponse(
        explain_stream(safe_coll, req.target, model=req.model, k=req.k, provider=req.provider),
        media_type="text/plain"
    )


@app.post("/bugs", response_model=BugResponse)
def bugs_endpoint(req: BugRequest):
    path = Path(req.file_path)
    if not path.exists():
        raise HTTPException(404, f"File not found: {req.file_path}")
    result = analyze_file(str(path), model=req.model)
    return BugResponse(analysis=result)


# ── Auto-Coder Agent endpoint ──────────────────────────────────────────────

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

@app.post("/agent", response_model=AgentResponse)
def agent_endpoint(req: AgentRequest):
    session_id = req.session_id
    if not session_id or not session_exists(session_id):
        session_id = str(uuid.uuid4())
        title = f"Agent: {req.task[:24]}..." if len(req.task) > 24 else f"Agent: {req.task}"
        create_session(session_id, title, user_email=req.user_email or "")

    append_message(session_id, "user", f"[Auto-Coder Task] {req.task}")

    try:
        result = run_agent(req.task, model=req.model, max_attempts=req.max_attempts)
        
        status_line = f"✅ **Success!** (after {result['attempts']} attempt{'s' if result['attempts'] > 1 else ''})" if result["success"] else f"❌ **Failed** (after {result['attempts']} attempts)"
        ai_msg = f"{status_line}\n\n```python\n{result['code']}\n```\n\n**Output:**\n```\n{result['stdout'] or result['stderr'] or result.get('error', 'No output.')}\n```"
        append_message(session_id, "ai", ai_msg)

        return AgentResponse(
            success=result["success"],
            attempts=result["attempts"],
            code=result["code"],
            stdout=result["stdout"],
            stderr=result["stderr"],
            error=result.get("error"),
            session_id=session_id
        )
    except Exception as e:
        err_msg = f"Agent execution failed: {str(e)}"
        append_message(session_id, "ai", f"❌ {err_msg}")
        raise HTTPException(500, err_msg)


# ── Unit Test Generator endpoint ───────────────────────────────────────────

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
    error: str | None = None
    session_id: str

@app.post("/tests", response_model=TestGenResponse)
def tests_endpoint(req: TestGenRequest):
    session_id = req.session_id
    if not session_id or not session_exists(session_id):
        session_id = str(uuid.uuid4())
        title = f"Tests: {req.target[:24]}"
        create_session(session_id, title, user_email=req.user_email or "")

    append_message(session_id, "user", f"[Generate Tests] {req.target} in {req.collection}")

    try:
        result = generate_tests_for_target(req.collection, req.target, model=req.model, max_attempts=req.max_attempts)
        status_line = f"✅ **Tests Passed in Docker!** ({result['attempts']} attempt{'s' if result['attempts'] > 1 else ''})" if result["success"] else f"⚠️ **Tests Failed** ({result['attempts']} attempts)"
        ai_msg = f"{status_line}\n\n```python\n{result['code']}\n```\n\n**Sandbox Execution:**\n```\n{result['stdout'] or result.get('error', 'No output.')}\n```"
        append_message(session_id, "ai", ai_msg)

        return TestGenResponse(
            success=result["success"],
            attempts=result["attempts"],
            code=result["code"],
            stdout=result["stdout"],
            error=result.get("error"),
            session_id=session_id
        )
    except Exception as e:
        err_msg = f"Test generation failed: {str(e)}"
        append_message(session_id, "ai", f"❌ {err_msg}")
        raise HTTPException(500, err_msg)


# ── GitHub Pull Request endpoint ───────────────────────────────────────────

class PRRequest(BaseModel):
    repo: str
    file_path: str
    new_content: str
    title: str
    description: str = "Automated fix generated by AI Code Assistant"
    base_branch: str = "main"

class PRResponse(BaseModel):
    status: str
    pr_url: str
    message: str

@app.post("/pr", response_model=PRResponse)
def pr_endpoint(req: PRRequest):
    try:
        url = create_fix_pr(
            repo_full_name=req.repo,
            file_path_in_repo=req.file_path,
            new_content=req.new_content,
            pr_title=req.title,
            pr_description=req.description,
            base_branch=req.base_branch,
        )
        return PRResponse(
            status="success",
            pr_url=url,
            message=f"Pull request created successfully: {url}"
        )
    except Exception as e:
        raise HTTPException(500, f"Failed to create PR: {str(e)}")