# AI Software Engineer — Autonomous Code Assistant

A full-stack AI code assistant that indexes GitHub repositories and lets you chat with, understand, debug, and safely execute code from a codebase using retrieval-augmented generation (RAG) and a self-correcting agent loop — running entirely on local, open-source models via Ollama (or swappable to Claude's API).

## Features

| Feature | Status |
|---|---|
| Repo indexing (AST-based chunking + vector embeddings) | ✅ Done |
| Chat with your codebase (RAG Q&A) | ✅ Done |
| Explain functions/classes (structured breakdown) | ✅ Done |
| Automated bug detection (static analysis + LLM reasoning) | ✅ Done |
| FastAPI backend (HTTP API for all features) | ✅ Done |
| Docker sandbox for safe, isolated code execution | ✅ Done |
| Self-correcting code generation (LangGraph agent loop) | ✅ Done |
| Automated unit test generation | 🟡 Partial — see note below |
| Pull request generation (GitHub API) | 🚧 In progress |
| Web frontend (React) with chat history | 🚧 In progress |
| Code quality metrics dashboard | 📋 Planned |

**Note on unit test generation:** works reliably for simple, low-dependency functions. On functions with multiple internal dependencies, smaller models (phi3) can introduce syntax errors while patching prior mistakes, and larger models (llama3.1) occasionally emit placeholder comments (`# same as original implementation`) instead of fully materializing dependent code. Addressable with tighter prompt constraints (explicitly disallowing placeholders) or by supplying full dependency source directly rather than asking the model to redeclare it — planned as a follow-up improvement.

## Architecture

```
                 ┌──────────────┐
                 │   FastAPI     │
                 │   Backend     │
                 └──────┬───────┘
                        │
     ┌──────────┬───────┼────────┬──────────────┐
     │          │       │        │              │
┌────▼────┐ ┌───▼───┐ ┌─▼──────┐ ┌▼───────────┐ ┌▼────────────┐
│ Indexer  │ │ Chat/ │ │  Bug   │ │ Code Agent │ │ Test        │
│ (AST +   │ │Explain│ │ Finder │ │ (LangGraph │ │ Generator   │
│  Chroma) │ │ (RAG) │ │(pylint │ │  self-     │ │ (LangGraph  │
│          │ │       │ │ + LLM) │ │ correcting)│ │ + sandbox)  │
└────┬─────┘ └───┬───┘ └───┬────┘ └─────┬──────┘ └──────┬──────┘
     │           │         │            │               │
     └───────────┴─────────┴─────┬──────┴───────────────┘
                                  │
                          ┌───────▼────────┐
                          │  Docker Sandbox │
                          │ (isolated exec, │
                          │ no network, CPU/│
                          │ memory limited, │
                          │ timeout-killed) │
                          └───────┬────────┘
                                  │
                          ┌───────▼────────┐
                          │   ChromaDB      │
                          │  Vector Store   │
                          └───────┬────────┘
                                  │
                          ┌───────▼────────┐
                          │     Ollama      │
                          │ (llama3.1/phi3/ │
                          │   Claude API)   │
                          └────────────────┘
```

## How it works

1. **Indexing** — clones a repo (or reads a local path), parses Python files with the `ast` module to chunk code at function/class boundaries (not naive fixed-size splitting), and embeds each chunk into a local ChromaDB vector store using Ollama's `nomic-embed-text` model.
2. **Retrieval** — a natural-language query is embedded the same way, and the top-k most similar code chunks are retrieved from the vector store.
3. **Generation** — retrieved chunks + the user's question are sent to a local LLM (`llama3.1` / `phi3`) or Claude's API, grounded strictly in the retrieved context to minimize hallucination. Every answer cites its source file and function name.
4. **Bug detection** — runs `pylint` static analysis on a target file, then uses the LLM to separate real logic/security issues from style noise, explaining *why* each real issue matters and suggesting a fix.
5. **Safe code execution** — any generated or analyzed code runs inside an isolated Docker container: no network access, capped memory/CPU, and a hard timeout that kills runaway processes (e.g. infinite loops) instead of hanging.
6. **Self-correcting generation** — a LangGraph state machine generates code, executes it in the sandbox, and on failure feeds the actual error message back into the next generation attempt (not a blind retry) — looping until the code works or a max-attempt limit is reached.
7. **Test generation** — reuses the same generate → execute → self-correct loop to write and validate pytest-style tests for a target function, retrieved via the same RAG pipeline as chat/explain.

## Tech stack

- **Python**, **LangChain**, **LangGraph** — RAG pipeline + self-correcting agent loop
- **FastAPI** — backend API
- **ChromaDB** — vector store
- **Docker** — isolated, safe code execution sandbox
- **Ollama** (`llama3.1`, `phi3`, `nomic-embed-text`) — local, free, offline inference
- **Claude API** — optional cloud backend, swappable via config
- **pylint / ast** — static analysis
- **GitPython** — repo cloning

## Setup

```bash
# 1. Clone this repo
git clone <this-repo-url>
cd project-ai

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate      # Windows
source venv/bin/activate      # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install Ollama (https://ollama.com) and pull models
ollama pull llama3.1
ollama pull phi3
ollama pull nomic-embed-text

# 5. Install Docker Desktop (https://docker.com/products/docker-desktop)
#    Windows users: requires WSL2 (wsl --install, then restart)
docker pull python:3.11-slim

# 6. (Optional) add ANTHROPIC_API_KEY to .env if using Claude instead of Ollama
```

## Usage

**CLI:**
```bash
# Index a repo
python indexer.py --local "C:\path\to\repo" --name my_repo

# Chat with it
python chat.py --name my_repo
You: How does the retriever module work?
You: explain chunk_python_file

# Find bugs in a specific file
python bug_finder.py --file path/to/file.py

# Run arbitrary code safely in the sandbox
python sandbox.py --code "print(1 + 1)"

# Self-correcting code generation
python code_agent.py --task "write a function that safely divides two numbers"

# Generate + validate unit tests for a function
python test_generator.py --name my_repo --target some_function_name
```

**API:**
```bash
uvicorn api:app --reload --port 8000
# Interactive docs: http://localhost:8000/docs
```

## Example: self-correcting agent loop

```
[agent] Task: write a function that reads a file called data.txt and prints its contents in uppercase
[agent] Finished after 2 attempt(s). Success: True

Attempt 1 crashed with an unhandled FileNotFoundError.
Attempt 2 (auto-generated fix based on that error) added a try/except
and ran successfully inside the Docker sandbox.
```

## Design decisions

- **AST-based chunking over fixed-size splitting** — preserves logical code boundaries (a full function stays together), which meaningfully improves retrieval relevance for code Q&A.
- **Model-agnostic backend** — same LangChain interface swaps between local Ollama models (free, private, offline) and Claude's API (higher quality, paid) without touching core logic.
- **Grounded generation** — the system prompt forces the LLM to answer only from retrieved context and explicitly say when it doesn't have enough information, reducing hallucination risk on code-specific questions.
- **Error-aware retries, not blind retries** — the self-correcting loop feeds the actual runtime error back into the next generation attempt, so the model fixes the real root cause instead of guessing again.
- **Sandbox-first safety** — no generated or analyzed code ever executes on the host machine; everything runs in a disposable, network-isolated, resource-capped container.

## Roadmap

- [x] Docker sandbox for safe, isolated code execution
- [x] LangGraph self-correcting agent loop: generate → execute → catch errors → fix → retry
- [x] Automated unit test generation (works on simple functions; complex-function reliability in progress)
- [ ] Automated pull request creation via GitHub API
- [ ] React frontend with persistent chat history
- [ ] Code quality metrics dashboard
Author

Built by Divesh as part of AI/LLM application engineering practice.
