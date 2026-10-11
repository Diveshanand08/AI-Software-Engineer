"""
api.py
Scalable FastAPI Application Entrypoint.
Assembles modular routers, lifecycle hooks, CORS middleware, and global error handling.

Usage:
    uvicorn api:app --reload --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import init_db
from core.exceptions import CodeAssistantException

from routers.sessions import router as sessions_router
from routers.indexing import router as indexing_router
from routers.chat import router as chat_router
from routers.code_ops import router as code_ops_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="RAG-powered AI Software Engineer: Repository Indexing, Code Chat, AST Bug Audits, and Auto-Coder.",
)

# ── CORS Middleware ────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Global Exception Handlers ──────────────────────────────────────────────
@app.exception_handler(CodeAssistantException)
async def code_assistant_exception_handler(request: Request, exc: CodeAssistantException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"status": "error", "message": exc.message},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"status": "error", "message": str(exc)},
    )


# ── Application Lifecycle ──────────────────────────────────────────────────
@app.on_event("startup")
def on_startup():
    """Ensure persistence layer tables and indexes are ready on boot."""
    init_db()
    print("[startup] SQLite chat database and schemas initialized.")


# ── Health Endpoints ───────────────────────────────────────────────────────
@app.get("/", tags=["Health"])
@app.get("/health", tags=["Health"])
def health_check():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
    }


# ── Mount Scalable Routers ─────────────────────────────────────────────────
app.include_router(indexing_router)
app.include_router(chat_router)
app.include_router(sessions_router)
app.include_router(code_ops_router)