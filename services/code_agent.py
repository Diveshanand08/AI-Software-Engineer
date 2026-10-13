"""
services/code_agent.py
Self-correcting code generation agent built with LangGraph and Docker sandbox verification.

Flow:
    generate code -> execute in sandbox -> error?
        -> yes: feed error back to LLM, regenerate (up to max_attempts)
        -> no:  done, return working code
"""

import argparse
import re
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from sandbox import run_code_in_sandbox
from core.config import settings

GENERATE_SYSTEM_PROMPT = """You are a Python code generator.
Given a task, write a single, complete, self-contained Python script that accomplishes it.

Rules:
- Output ONLY the Python code, wrapped in a single ```python code block. No explanation before or after.
- The script must be runnable as-is (no missing imports, no placeholders).
- Include a print statement so the output is visible when run.
- If given error feedback from a previous attempt, fix the actual root cause - don't just suppress the error.
"""


class CodeAgentState(TypedDict):
    task: str
    code: str
    stdout: str
    stderr: str
    error: Optional[str]
    attempts: int
    max_attempts: int
    model: str
    provider: Optional[str]
    success: bool
    history: list[str]


def _extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*\n?(.*?)(?:```|$)", text, re.DOTALL)
    if match and match.group(1).strip():
        code = match.group(1).strip()
    else:
        code = text.strip()

    lines = code.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def generate_code_node(state: CodeAgentState) -> CodeAgentState:
    from llm import generate
    provider = state.get("provider") or ("gemini" if settings.GEMINI_API_KEY else "ollama")

    if state.get("error"):
        user_prompt = f"""Task: {state['task']}

Previous attempt:
```python
{state['code']}
```

This failed with the following error:
{state['error']}

Fix the code to resolve this error. Output the full corrected script."""
    else:
        user_prompt = f"Task: {state['task']}"

    messages = [
        {"role": "system", "content": GENERATE_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    try:
        raw_res = generate(messages, provider=provider, ollama_model=state.get("model", "phi3"))
    except Exception as e:
        if provider != "gemini" and settings.GEMINI_API_KEY:
            raw_res = generate(messages, provider="gemini")
        else:
            raise e

    code = _extract_code(raw_res)
    state["code"] = code
    state["attempts"] += 1
    state["history"].append(f"--- Attempt {state['attempts']} ---\n{code}")
    return state


def execute_code_node(state: CodeAgentState) -> CodeAgentState:
    result = run_code_in_sandbox(state["code"], timeout=10)

    if result.error:
        state["error"] = f"Sandbox error: {result.error}"
        state["stdout"] = ""
        state["stderr"] = ""
        state["success"] = False
        return state

    if result.timed_out:
        state["error"] = "Execution timed out (possible infinite loop)."
        state["stdout"] = result.stdout
        state["stderr"] = ""
        state["success"] = False
        return state

    state["stdout"] = result.stdout
    state["stderr"] = result.stderr

    if result.exit_code == 0:
        state["error"] = None
        state["success"] = True
    else:
        state["error"] = result.stderr or f"Non-zero exit code: {result.exit_code}"
        state["success"] = False

    return state


def should_retry(state: CodeAgentState) -> str:
    if state["success"]:
        return "done"
    if state["attempts"] >= state["max_attempts"]:
        return "give_up"
    return "retry"


def build_graph():
    graph = StateGraph(CodeAgentState)
    graph.add_node("generate", generate_code_node)
    graph.add_node("execute", execute_code_node)

    graph.set_entry_point("generate")
    graph.add_edge("generate", "execute")
    graph.add_conditional_edges(
        "execute",
        should_retry,
        {"retry": "generate", "done": END, "give_up": END},
    )
    return graph.compile()


def run_agent(task: str, model: str = "phi3", max_attempts: int = 3, provider: str = "gemini") -> CodeAgentState:
    """Execute the multi-attempt code generation and sandbox testing workflow."""
    app = build_graph()
    initial_state: CodeAgentState = {
        "task": task,
        "code": "",
        "stdout": "",
        "stderr": "",
        "error": None,
        "attempts": 0,
        "max_attempts": max_attempts,
        "model": model,
        "provider": provider,
        "success": False,
        "history": [],
    }
    final_state = app.invoke(initial_state)
    return final_state


def main():
    parser = argparse.ArgumentParser(description="Self-correcting code generation agent.")
    parser.add_argument("--task", required=True, help="Natural language description of the code to generate")
    parser.add_argument("--model", default="phi3", help="Ollama model to use")
    parser.add_argument("--max-attempts", type=int, default=3, help="Max generate/fix retries")
    args = parser.parse_args()

    print(f"[agent] Task: {args.task}")
    print(f"[agent] Model: {args.model}, max attempts: {args.max_attempts}\n")

    result = run_agent(args.task, model=args.model, max_attempts=args.max_attempts)

    print(f"\n[agent] Finished after {result['attempts']} attempt(s). Success: {result['success']}\n")

    if result["success"]:
        print("--- Final working code ---")
        print(result["code"])
        print("\n--- Output ---")
        print(result["stdout"])
    else:
        print("--- Gave up. Last attempt ---")
        print(result["code"])
        print("\n--- Last error ---")
        print(result["error"])


if __name__ == "__main__":
    main()
