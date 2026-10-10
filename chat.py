"""
chat.py
Interactive chat loop with two modes:
  1. Ask     - free-form Q&A about the codebase
  2. Explain - structured explanation of a specific function/class

Usage:
    python chat.py --name test_repo
    python chat.py --name test_repo --provider gemini
"""

import argparse

from retriever import retrieve, format_for_prompt
from llm import generate, generate_stream

SYSTEM_PROMPT = """You are a senior code assistant answering questions about a specific codebase.
You will be given relevant code snippets retrieved from the repo, followed by a question.

Rules:
- Answer using ONLY the provided code context. If the context doesn't contain enough
  information to answer confidently, say so explicitly.
- You MUST format your response using rich Markdown.
- Use **bold text** for file names, function names, and key concepts.
- Use `inline code` for variables or small snippets.
- Use numbered lists or bullet points to break down complex logic.
- Use ```python ... ``` blocks if providing code examples.
- Keep answers concise and technical.
"""

EXPLAIN_SYSTEM_PROMPT = """You are a code assistant that explains functions/classes in a structured way.
You will be given the target function's code plus related context from the same repo.

Respond in EXACTLY this structure:
**Purpose:** (1-2 sentences on what this does and why it exists)
**Parameters:** (list each param and its role; say "None" if no params)
**Logic flow:** (numbered steps of what happens, in order)
**Edge cases / risks:** (what could go wrong, unhandled inputs, or assumptions made)

Format using rich Markdown. Use inline code for variable names.
Be concise. Do not repeat the raw code back verbatim. Base everything only on the provided context.
"""


def build_prompt(question: str, context: str) -> str:
    return f"""Here is relevant code context retrieved from the repository:

{context}

---

Question: {question}

Answer based on the code context above."""


def _messages(system_prompt: str, user_prompt: str) -> list[dict]:
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _run_llm(system_prompt: str, user_prompt: str, model: str, provider: str) -> str:
    return generate(_messages(system_prompt, user_prompt), provider, ollama_model=model)


def _sources_block(results: list[dict]) -> str:
    sources = sorted(set(f"{r['file']} :: {r['name']}" for r in results))
    return "\n".join(f"  - {s}" for s in sources)


def _explain_prompt(context: str, target_name: str) -> str:
    return f"""Here is code context from the repository:

{context}

---

Explain the function/class named: {target_name}"""


def ask(collection_name: str, question: str, model: str, k: int = 4, provider: str = "ollama") -> str:
    """Free-form Q&A about the codebase."""
    results = retrieve(collection_name, question, k=k)
    if not results:
        return "No relevant code found in the index for this question."

    context = format_for_prompt(results)
    answer = _run_llm(SYSTEM_PROMPT, build_prompt(question, context), model, provider)
    return f"{answer}\n\n**Sources:**\n{_sources_block(results)}"


def explain(collection_name: str, target_name: str, model: str, k: int = 4, provider: str = "ollama") -> str:
    """Structured explanation of a specific function/class by name."""
    results = retrieve(collection_name, target_name, k=k)
    if not results:
        return f"Could not find anything matching '{target_name}' in the index."

    context = format_for_prompt(results)
    answer = _run_llm(EXPLAIN_SYSTEM_PROMPT, _explain_prompt(context, target_name), model, provider)
    return f"{answer}\n\n**Sources:**\n{_sources_block(results)}"


# --- STREAMING FUNCTIONS ---

def ask_stream(collection_name: str, question: str, model: str, k: int = 4, provider: str = "ollama"):
    """Streams the Q&A response token by token."""
    results = retrieve(collection_name, question, k=k)
    if not results:
        yield "No relevant code found in the index for this question."
        return

    context = format_for_prompt(results)
    messages = _messages(SYSTEM_PROMPT, build_prompt(question, context))

    for piece in generate_stream(messages, provider, ollama_model=model):
        yield piece

    yield f"\n\n**Sources:**\n{_sources_block(results)}"


def explain_stream(collection_name: str, target_name: str, model: str, k: int = 4, provider: str = "ollama"):
    """Streams the explanation response token by token."""
    results = retrieve(collection_name, target_name, k=k)
    if not results:
        yield f"Could not find anything matching '{target_name}' in the index."
        return

    context = format_for_prompt(results)
    messages = _messages(EXPLAIN_SYSTEM_PROMPT, _explain_prompt(context, target_name))

    for piece in generate_stream(messages, provider, ollama_model=model):
        yield piece

    yield f"\n\n**Sources:**\n{_sources_block(results)}"


def chat_loop(collection_name: str, model: str, k: int = 4, provider: str = "ollama"):
    print(f"[chat] Loaded collection '{collection_name}', provider '{provider}', model '{model}'.")
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
                answer = explain(collection_name, target, model=model, k=k, provider=provider)
            elif raw.lower().startswith("ask "):
                question = raw[len("ask "):].strip()
                answer = ask(collection_name, question, model=model, k=k, provider=provider)
            else:
                answer = ask(collection_name, raw, model=model, k=k, provider=provider)
        except Exception as e:
            print(f"[chat] Error: {e}\n")
            continue

        print(f"Assistant: {answer}\n")


def main():
    parser = argparse.ArgumentParser(description="Chat with your indexed codebase.")
    parser.add_argument("--name", required=True, help="Collection name used during indexing")
    parser.add_argument("--model", default="phi3", help="Ollama model (used when provider=ollama)")
    parser.add_argument("--provider", default="ollama", help="ollama | groq | gemini")
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve per question")
    args = parser.parse_args()

    chat_loop(args.name, model=args.model, k=args.k, provider=args.provider)


if __name__ == "__main__":
    main()