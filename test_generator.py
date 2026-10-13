"""
test_generator.py
Generates pytest unit tests for a target function/class from the indexed
codebase, then validates the generated tests actually run correctly inside
the Docker sandbox - self-correcting if the tests have errors.

Usage:
    python test_generator.py --name test_repo --target chunk_python_file
    python test_generator.py --name test_repo --target chunk_python_file --max-attempts 3
"""

import argparse
import os
import re
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END
from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from retriever import retrieve, format_for_prompt
from sandbox import run_code_in_sandbox

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

TEST_GEN_SYSTEM_PROMPT = """You are a Python test engineer writing pytest unit tests.

You will be given the source code of a target function/class plus related context
from the same repository.

Rules:
- Write a SINGLE self-contained Python script using pytest-style assert statements
  (no need to import pytest itself - use plain `assert` statements in test functions).
- Re-define or stub any dependencies needed so the script runs standalone (the target
  function's own code must be included/redefined in the script since it won't be
  importable in the sandbox).
- Include at least 2-3 test cases covering normal input, an edge case, and an
  invalid/empty input if relevant.
- At the end of the script, call each test function and print "ALL TESTS PASSED"
  only if every assertion succeeds. Let AssertionErrors propagate normally otherwise.
- Output ONLY the Python code in a single ```python code block. No explanation.
- If given error feedback from a previous attempt, fix the actual root cause.
"""


class TestGenState(TypedDict):
    target: str
    context: str
    code: str
    stdout: str
    stderr: str
    error: Optional[str]
    attempts: int
    max_attempts: int
    model: str
    provider: Optional[str]
    success: bool


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


def generate_tests_node(state: TestGenState) -> TestGenState:
    from llm import generate
    provider = state.get("provider") or ("gemini" if os.getenv("GEMINI_API_KEY") else "ollama")

    if state.get("error"):
        user_prompt = f"""Target: {state['target']}

Code context:
{state['context']}

Previous test script attempt:
```python
{state['code']}
```

This failed with:
{state['error']}

Fix the test script to resolve this error."""
    else:
        user_prompt = f"""Target function/class to test: {state['target']}

Code context from the repository:
{state['context']}

Write a self-contained pytest-style test script for this target."""

    messages = [
        {"role": "system", "content": TEST_GEN_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
    try:
        raw_res = generate(messages, provider=provider, ollama_model=state.get("model", "phi3"))
    except Exception as e:
        if provider != "gemini" and os.getenv("GEMINI_API_KEY"):
            raw_res = generate(messages, provider="gemini")
        else:
            raise e

    code = _extract_code(raw_res)
    state["code"] = code
    state["attempts"] += 1
    return state


def execute_tests_node(state: TestGenState) -> TestGenState:
    result = run_code_in_sandbox(state["code"], timeout=15)

    if result.error:
        state["error"] = f"Sandbox error: {result.error}"
        state["success"] = False
        return state

    if result.timed_out:
        state["error"] = "Test execution timed out."
        state["success"] = False
        return state

    state["stdout"] = result.stdout
    state["stderr"] = result.stderr

    if result.exit_code == 0 and "ALL TESTS PASSED" in result.stdout:
        state["error"] = None
        state["success"] = True
    else:
        state["error"] = result.stderr or "Tests did not report ALL TESTS PASSED."
        state["success"] = False

    return state


def should_retry(state: TestGenState) -> str:
    if state["success"]:
        return "done"
    if state["attempts"] >= state["max_attempts"]:
        return "give_up"
    return "retry"


def build_graph():
    graph = StateGraph(TestGenState)
    graph.add_node("generate", generate_tests_node)
    graph.add_node("execute", execute_tests_node)

    graph.set_entry_point("generate")
    graph.add_edge("generate", "execute")
    graph.add_conditional_edges(
        "execute",
        should_retry,
        {"retry": "generate", "done": END, "give_up": END},
    )
    return graph.compile()


def generate_tests_for_target(collection_name: str, target: str, model: str = "phi3", max_attempts: int = 3, k: int = 4, provider: str = "gemini") -> TestGenState:
    results = retrieve(collection_name, target, k=k)
    if not results:
        raise ValueError(f"No context found for '{target}' in collection '{collection_name}'")

    context = format_for_prompt(results)

    app = build_graph()
    initial_state: TestGenState = {
        "target": target,
        "context": context,
        "code": "",
        "stdout": "",
        "stderr": "",
        "error": None,
        "attempts": 0,
        "max_attempts": max_attempts,
        "model": model,
        "provider": provider,
        "success": False,
    }
    return app.invoke(initial_state)


def main():
    parser = argparse.ArgumentParser(description="Generate and validate pytest unit tests for a function/class.")
    parser.add_argument("--name", required=True, help="Indexed collection name")
    parser.add_argument("--target", required=True, help="Function/class name to generate tests for")
    parser.add_argument("--model", default="phi3", help="Ollama model to use")
    parser.add_argument("--max-attempts", type=int, default=3)
    args = parser.parse_args()

    print(f"[test_gen] Generating tests for '{args.target}' in '{args.name}'...\n")

    result = generate_tests_for_target(args.name, args.target, model=args.model, max_attempts=args.max_attempts)

    print(f"\n[test_gen] Finished after {result['attempts']} attempt(s). Success: {result['success']}\n")

    if result["success"]:
        print("--- Generated test script (validated, passing) ---")
        print(result["code"])
        print("\n--- Test output ---")
        print(result["stdout"])
    else:
        print("--- Gave up. Last attempt ---")
        print(result["code"])
        print("\n--- Last error ---")
        print(result["error"])


if __name__ == "__main__":
    main()