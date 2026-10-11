"""
routers/code_ops.py
FastAPI router for static code analysis, auto-coder agent, unit test synthesis, and GitHub PR creation.
"""

import uuid
from pathlib import Path
from fastapi import APIRouter, HTTPException

from core.database import session_exists, create_session, append_message
from bug_finder import analyze_file
from services.code_agent import run_agent
from test_generator import generate_tests_for_target
from pr_generator import create_fix_pr
from schemas.chat import (
    BugRequest,
    BugResponse,
    AgentRequest,
    AgentResponse,
    TestGenRequest,
    TestGenResponse,
    PRRequest,
    PRResponse,
)

router = APIRouter(prefix="", tags=["Code Operations"])


@router.post("/bugs", response_model=BugResponse)
def bugs_endpoint(req: BugRequest):
    """Run AST and static code analysis to detect potential bugs and security vulnerabilities."""
    path = Path(req.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {req.file_path}")
    result = analyze_file(str(path), model=req.model)
    return BugResponse(analysis=result)


@router.post("/agent", response_model=AgentResponse)
def agent_endpoint(req: AgentRequest):
    """Run the self-correcting Auto-Coder LangGraph agent in an isolated Docker sandbox."""
    session_id = req.session_id
    if not session_id or not session_exists(session_id):
        session_id = str(uuid.uuid4())
        title = f"Agent: {req.task[:24]}..." if len(req.task) > 24 else f"Agent: {req.task}"
        create_session(session_id, title, user_email=req.user_email or "")

    append_message(session_id, "user", f"[Auto-Coder Task] {req.task}")

    try:
        result = run_agent(req.task, model=req.model, max_attempts=req.max_attempts)

        status_line = (
            f"✅ **Success!** (after {result['attempts']} attempt{'s' if result['attempts'] > 1 else ''})"
            if result["success"]
            else f"❌ **Failed** (after {result['attempts']} attempts)"
        )
        ai_msg = (
            f"{status_line}\n\n```python\n{result['code']}\n```\n\n"
            f"**Output:**\n```\n{result['stdout'] or result['stderr'] or result.get('error', 'No output.')}\n```"
        )
        append_message(session_id, "ai", ai_msg)

        return AgentResponse(
            success=result["success"],
            attempts=result["attempts"],
            code=result["code"],
            stdout=result["stdout"],
            stderr=result["stderr"],
            error=result["error"],
            session_id=session_id,
        )
    except Exception as e:
        err_msg = f"Agent failed: {str(e)}"
        append_message(session_id, "ai", f"❌ {err_msg}")
        raise HTTPException(status_code=500, detail=err_msg)


@router.post("/tests", response_model=TestGenResponse)
def tests_endpoint(req: TestGenRequest):
    """Generate self-contained unit tests for a target function and verify them in a sandbox container."""
    session_id = req.session_id
    if not session_id or not session_exists(session_id):
        session_id = str(uuid.uuid4())
        title = f"Tests: {req.target[:24]}"
        create_session(session_id, title, user_email=req.user_email or "")

    append_message(session_id, "user", f"[Generate Tests] {req.target} in {req.collection}")

    try:
        result = generate_tests_for_target(
            req.collection, req.target, model=req.model, max_attempts=req.max_attempts
        )
        status_line = (
            f"✅ **Tests Passed in Docker!** ({result['attempts']} attempt{'s' if result['attempts'] > 1 else ''})"
            if result["success"]
            else f"⚠️ **Tests Failed** ({result['attempts']} attempts)"
        )
        ai_msg = (
            f"{status_line}\n\n```python\n{result['code']}\n```\n\n"
            f"**Sandbox Execution:**\n```\n{result['stdout'] or result.get('error', 'No output.')}\n```"
        )
        append_message(session_id, "ai", ai_msg)

        return TestGenResponse(
            success=result["success"],
            attempts=result["attempts"],
            code=result["code"],
            stdout=result["stdout"],
            stderr=result.get("stderr", ""),
            error=result.get("error"),
            session_id=session_id,
        )
    except Exception as e:
        err_msg = f"Test generation failed: {str(e)}"
        append_message(session_id, "ai", f"❌ {err_msg}")
        raise HTTPException(status_code=500, detail=err_msg)


@router.post("/pr", response_model=PRResponse)
def pr_endpoint(req: PRRequest):
    """Commit code and submit a Pull Request to a target GitHub repository."""
    try:
        url = create_fix_pr(
            repo_full_name=req.repo_full_name,
            file_path_in_repo=req.file_path,
            new_content=req.code_content,
            pr_title=req.title,
            pr_description=req.description,
        )
        return PRResponse(
            success=True,
            pr_url=url,
            branch="ai-fix",
            message=f"Pull request created successfully: {url}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create PR: {str(e)}")
