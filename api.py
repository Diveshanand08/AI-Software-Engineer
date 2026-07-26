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

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from indexer import clone_repo, collect_documents, build_index
from chat import ask as chat_ask, explain as chat_explain
from bug_finder import analyze_file

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


# ---- request/response models ----

class IndexRequest(BaseModel):
    name: str
    repo_url: str | None = None
    local_path: str | None = None


class IndexResponse(BaseModel):
    name: str
    files_scanned: int
    chunks_indexed: int


class AskRequest(BaseModel):
    collection: str
    question: str
    model: str = "phi3"
    k: int = 4


class ExplainRequest(BaseModel):
    collection: str
    target: str
    model: str = "phi3"
    k: int = 4


class AnswerResponse(BaseModel):
    answer: str


class BugRequest(BaseModel):
    file_path: str
    model: str = "phi3"


class BugResponse(BaseModel):
    analysis: str


# ---- endpoints ----

@app.get("/")
def root():
    return {"status": "ok", "service": "AI Code Assistant API"}


@app.post("/index", response_model=IndexResponse)
def index_repo(req: IndexRequest):
    if not req.repo_url and not req.local_path:
        raise HTTPException(400, "Provide either repo_url or local_path")

    if req.local_path:
        repo_path = Path(req.local_path).resolve()
        if not repo_path.exists():
            raise HTTPException(404, f"Local path not found: {req.local_path}")
    else:
        repo_path = clone_repo(req.repo_url, req.name)

    documents = collect_documents(repo_path)
    if not documents:
        raise HTTPException(422, "No indexable code files found in this repo")

    build_index(documents, collection_name=req.name)

    files_scanned = len(set(doc.metadata["file"] for doc in documents))
    return IndexResponse(name=req.name, files_scanned=files_scanned, chunks_indexed=len(documents))


@app.post("/ask", response_model=AnswerResponse)
def ask_endpoint(req: AskRequest):
    try:
        answer = chat_ask(req.collection, req.question, model=req.model, k=req.k)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return AnswerResponse(answer=answer)


@app.post("/explain", response_model=AnswerResponse)
def explain_endpoint(req: ExplainRequest):
    try:
        answer = chat_explain(req.collection, req.target, model=req.model, k=req.k)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return AnswerResponse(answer=answer)


@app.post("/bugs", response_model=BugResponse)
def bugs_endpoint(req: BugRequest):
    path = Path(req.file_path)
    if not path.exists():
        raise HTTPException(404, f"File not found: {req.file_path}")
    result = analyze_file(str(path), model=req.model)
    return BugResponse(analysis=result)



