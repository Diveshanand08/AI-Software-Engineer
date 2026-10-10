"""
api.py
FastAPI backend exposing the code assistant's core features as HTTP endpoints:
  POST /index    - index a repo (local path or git URL)
  POST /ask      - free-form Q&A about an indexed repo
  POST /explain  - structured explanation of a function/class
  POST /bugs     - run bug detection on a specific file

Usage:
    uvicorn api:app --reload --port 8000

Then visit http://localhost:8000/docs for interactive Swagger UI.
"""

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

from indexer import clone_repo, collect_documents, build_index
from chat import ask as chat_ask, explain as chat_explain
from llm import available_providers
from bug_finder import analyze_file
from chat import ask_stream, explain_stream

app = FastAPI(
    title="AI Code Assistant API",
    description="RAG-based code assistant: index repos, chat, explain functions, find bugs.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # dev only - restrict this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- global storage ----
# In-memory storage for chat sessions
# Structure: { "session_id": { "id": "...", "title": "...", "created_at": "...", "messages": [...] } }
CHAT_SESSIONS = {}

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
    session_id: str | None = None  # Frontend will pass this to continue a chat
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
    except Exception as e:
        print(f"[background] Indexing failed for '{name}': {e}")


# ---- endpoints ----
@app.get("/")
def root():
    return {"status": "ok", "service": "AI Code Assistant API"}
@app.get("/providers")
def providers():
    return available_providers()

@app.get("/sessions")
def get_all_sessions():
    """Returns metadata for all sessions to populate the sidebar."""
    sessions_list = [
        {"id": sid, "title": data["title"], "created_at": data["created_at"]}
        for sid, data in CHAT_SESSIONS.items()
    ]
    # Sort newest first
    sessions_list.sort(key=lambda x: x["created_at"], reverse=True)
    return sessions_list

@app.get("/sessions/{session_id}")
def get_session_messages(session_id: str):
    """Returns the full message array for a specific session."""
    if session_id not in CHAT_SESSIONS:
        raise HTTPException(404, "Session not found")
    return CHAT_SESSIONS[session_id]["messages"]

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
    # 1. Handle Session ID creation or retrieval
    session_id = req.session_id
    if not session_id or session_id not in CHAT_SESSIONS:
        session_id = str(uuid.uuid4())
        title = req.question[:30] + "..." if len(req.question) > 30 else req.question
        CHAT_SESSIONS[session_id] = {
            "id": session_id,
            "title": title,
            "created_at": datetime.now().isoformat(),
            "messages": []
        }

    # 2. Save the user's question to history immediately
    CHAT_SESSIONS[session_id]["messages"].append({
        "role": "user",
        "content": req.question
    })

    # 3. Wrapper generator to capture the streamed output
    def stream_and_save():
        # Tell the frontend the session_id first
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
                CHAT_SESSIONS[session_id]["messages"].append({
                    "role": "ai",
                    "content": full_ai_response
                })

    return StreamingResponse(
        stream_and_save(),
        media_type="text/plain"
    )

@app.post("/explain")
def explain_endpoint(req: ExplainRequest):
    return StreamingResponse(
        explain_stream(req.collection, req.target, model=req.model, k=req.k),
        media_type="text/plain"
    )

@app.post("/bugs", response_model=BugResponse)
def bugs_endpoint(req: BugRequest):
    path = Path(req.file_path)
    if not path.exists():
        raise HTTPException(404, f"File not found: {req.file_path}")
    result = analyze_file(str(path), model=req.model)
    return BugResponse(analysis=result)