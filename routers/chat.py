"""
routers/chat.py
FastAPI router for AI assistant Q&A, structured function explanations, and model provider discovery.
"""

import uuid
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from core.database import session_exists, create_session, append_message
from chat import ask_stream, explain_stream
from llm import available_providers
from routers.indexing import sanitize_collection_name
from schemas.chat import AskRequest, ExplainRequest

router = APIRouter(prefix="", tags=["Chat"])


@router.get("/providers")
def list_providers():
    """List available LLM providers based on configured credentials."""
    return available_providers()


@router.post("/ask")
def ask_endpoint(req: AskRequest):
    """Stream free-form Q&A response regarding the indexed codebase."""
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


@router.post("/explain")
def explain_endpoint(req: ExplainRequest):
    """Stream structured purpose/parameter/logic/edge-case explanation of a specific function or class."""
    safe_coll = sanitize_collection_name(req.collection)
    return StreamingResponse(
        explain_stream(safe_coll, req.target, model=req.model, k=req.k, provider=req.provider),
        media_type="text/plain",
    )
