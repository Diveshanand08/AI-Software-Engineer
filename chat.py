"""
chat.py
Interactive chat loop with two modes:
  1. Ask     - free-form Q&A about the codebase
  2. Explain - structured explanation of a specific function/class

Usage:
    python chat.py --name test_repo
    python chat.py --name test_repo --model phi3
"""

import argparse
import os

from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

from retriever import retrieve, format_for_prompt

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

SYSTEM_PROMPT = """You are a code assistant answering questions about a specific codebase.
You will be given relevant code snippets retrieved from the repo, followed by a question.

Rules:
- Answer using ONLY the provided code context. If the context doesn't contain enough
  information to answer confidently, say so explicitly rather than guessing.
- Reference specific function/file names from the context in your answer.
- Keep answers concise and technical. Assume the user is a developer, not a beginner.
"""

EXPLAIN_SYSTEM_PROMPT = """You are a code assistant that explains functions/classes in a structured way.
You will be given the target function's code plus related context from the same repo.

Respond in EXACTLY this structure:
Purpose: (1-2 sentences on what this does and why it exists)
Parameters: (list each param and its role; say "None" if no params)
Logic flow: (numbered steps of what happens, in order)
Edge cases / risks: (what could go wrong, unhandled inputs, or assumptions made)

Be concise. Do not repeat the raw code back verbatim. Base everything only on the provided context.
"""


def build_prompt(question: str, context: str) -> str:
    return f"""Here is relevant code context retrieved from the repository:

{context}

---

Question: {question}

Answer based on the code context above."""


def _run_llm(system_prompt: str, user_prompt: str, model: str) -> str:
    llm = ChatOllama(model=model, base_url=OLLAMA_BASE_URL, temperature=0.2)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    response = llm.invoke(messages)
    return response.content


def _sources_block(results: list[dict]) -> str:
    sources = sorted(set(f"{r['file']} :: {r['name']}" for r in results))
    return "\n".join(f"  - {s}" for s in sources)


def ask(collection_name: str, question: str, model: str, k: int = 4) -> str:
    """Free-form Q&A about the codebase."""
    results = retrieve(collection_name, question, k=k)
    if not results:
        return "No relevant code found in the index for this question."

    context = format_for_prompt(results)
    user_prompt = build_prompt(question, context)
    answer = _run_llm(SYSTEM_PROMPT, user_prompt, model)
    return f"{answer}\n\nSources:\n{_sources_block(results)}"


def explain(collection_name: str, target_name: str, model: str, k: int = 4) -> str:
    """Structured explanation of a specific function/class by name."""
    results = retrieve(collection_name, target_name, k=k)
    if not results:
        return f"Could not find anything matching '{target_name}' in the index."

    context = format_for_prompt(results)
    user_prompt = f"""Here is code context from the repository:

{context}

---

Explain the function/class named: {target_name}"""

    answer = _run_llm(EXPLAIN_SYSTEM_PROMPT, user_prompt, model)
    return f"{answer}\n\nSources:\n{_sources_block(results)}"


def chat_loop(collection_name: str, model: str, k: int = 4):
    print(f"[chat] Loaded collection '{collection_name}', model '{model}'.")
    print("[chat] Commands:")
    print("  ask <question>       - free-form Q&A")
    print("  explain <name>       - structured explanation of a function/class")
    print("  exit                 - quit\n")

    while True:
        try:
            raw = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[chat] Bye.")
            break

        if not raw:
            continue
        if raw.lower() in ("exit", "quit"):
            print("[chat] Bye.")
            break

        print("\n[thinking...]\n")
        try:
            if raw.lower().startswith("explain "):
                target = raw[len("explain "):].strip()
                answer = explain(collection_name, target, model=model, k=k)
            elif raw.lower().startswith("ask "):
                question = raw[len("ask "):].strip()
                answer = ask(collection_name, question, model=model, k=k)
            else:
                answer = ask(collection_name, raw, model=model, k=k)
        except Exception as e:
            print(f"[chat] Error: {e}\n")
            continue

        print(f"Assistant: {answer}\n")


def main():
    parser = argparse.ArgumentParser(description="Chat with your indexed codebase.")
    parser.add_argument("--name", required=True, help="Collection name used during indexing")
    parser.add_argument("--model", default="phi3", help="Ollama model to use")
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve per question")
    args = parser.parse_args()

    chat_loop(args.name, model=args.model, k=args.k)


if __name__ == "__main__":
    main()
