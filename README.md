# CodeAssist — AI Software Engineer / Autonomous Code Assistant

A full-stack AI code assistant that indexes GitHub repositories and lets you chat with, understand, debug, and safely execute code from a codebase — combining retrieval-augmented generation (RAG), a self-correcting agent loop, sandboxed execution, and automated GitHub pull requests. Runs entirely on local, open-source models via Ollama (swappable to Claude's API).

## Features

| Feature | Status |
|---|---|
| Repo indexing (AST-based chunking + vector embeddings, batched for large repos) | Done |
| Chat with your codebase (RAG Q&A, grounded + cited) | Done |
| Explain functions/classes (structured breakdown) | Done |
| Automated bug detection (static analysis + LLM reasoning) | Done |
| FastAPI backend (HTTP API for all features, CORS-enabled) | Done |
| Docker sandbox for safe, isolated code execution | Done |
| Self-correcting code generation (LangGraph agent loop) | Done |
| Automated unit test generation (LangGraph + Docker sandbox) | Done |
| Pull request generation (GitHub API + git) | Done |
| React frontend with chat interface & Google Sign-In | Done |
| Persistent chat history across sessions (SQLite + user isolation) | Done |

**Note on unit test generation:** works reliably for simple, low-dependency functions. On functions with multiple internal dependencies, smaller models (phi3) can introduce syntax errors while patching prior mistakes, and larger models (llama3.1) occasionally emit placeholder comments (`# same as original implementation`) instead of fully materializing dependent code. Addressable with tighter prompt constraints or by supplying full dependency source directly — planned as a follow-up improvement.

## Screenshots

**Chat — grounded answer over a real, unfamiliar codebase (the `requests` library):**
> Asked "How does the Session class handle cookies?" — the assistant correctly cited `src/requests/sessions.py`, `src/requests/cookies.py`, and even flagged a contradiction it noticed in a test case (`test_request_cookies_not_persisted`), all grounded in retrieved source, not memorized/hallucinated knowledge.

**Self-correcting agent — real multi-attempt fix:**
```
[agent] Task: write a function that reads a file called data.txt and prints its contents in uppercase
[agent] Finished after 2 attempt(s). Success: True

Attempt 1 crashed with an unhandled FileNotFoundError.
Attempt 2 (auto-generated fix based on that error) added a try/except
and ran successfully inside the Docker sandbox.
```

**PR generation — verified live:** branch created, committed, pushed, and PR opened/merged automatically against this repo (see closed PR #1).

## Architecture

```
                    ┌──────────────────┐
                    │  React Frontend   │
                    │ (Chat / Explain / │
                    │   Find Bugs UI)   │
                    └─────────┬────────┘
                              │ HTTP
                    ┌─────────▼────────┐
                    │   FastAPI Backend │
                    └─────────┬────────┘
                              │
       ┌───────────┬──────────┼──────────┬──────────────┐
       │           │          │          │              │
 ┌─────▼─────┐ ┌───▼───┐ ┌────▼───┐ ┌────▼─────┐  ┌─────▼──────┐
 │  Indexer   │ │ Chat/ │ │  Bug   │ │   Code    │  │    Test     │
 │ (AST +     │ │Explain│ │ Finder │ │   Agent   │  │  Generator  │
 │  Chroma)   │ │ (RAG) │ │(pylint │ │(LangGraph │  │ (LangGraph  │
 │            │ │       │ │ + LLM) │ │ self-     │  │ + sandbox)  │
 │            │ │       │ │        │ │ correcting)│  │             │
 └─────┬─────┘ └───┬───┘ └───┬────┘ └─────┬─────┘  └──────┬──────┘
       │           │         │            │               │
       └───────────┴─────────┴─────┬──────┴───────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   Docker Sandbox    │
                          │ (isolated exec, no   │
                          │  network, CPU/memory │
                          │  limited, timeout-   │
                          │       killed)        │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │     ChromaDB        │
                          │   Vector Store      │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │       Ollama         │
                          │ (llama3.1 / phi3 /   │
                          │    Claude API)       │
                          └────────────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   GitHub API + git   │
                          │ (branch, commit,     │
                          │  push, open PR)      │
                          └────────────────────┘
```

## How it works

1. **Indexing** — clones a repo (or reads a local path), parses Python files with the `ast` module to chunk code at function/class boundaries, and embeds each chunk into a local ChromaDB vector store using Ollama's `nomic-embed-text` model, in batches to handle large repos reliably (validated on the real `requests` library — 817 chunks across 37 files).
2. **Retrieval** — a natural-language query is embedded the same way, and the top-k most similar code chunks are retrieved from the vector store.
3. **Generation** — retrieved chunks + the user's question are sent to a local LLM (`llama3.1` / `phi3`) or Claude's API, grounded strictly in the retrieved context to minimize hallucination. Every answer cites its source file and function name.
4. **Bug detection** — runs `pylint` static analysis on a target file, then uses the LLM to separate real logic/security issues from style noise, explaining *why* each real issue matters and suggesting a fix.
5. **Safe code execution** — any generated or analyzed code runs inside an isolated Docker container: no network access, capped memory/CPU, and a hard timeout that kills runaway processes instead of hanging.
6. **Self-correcting generation** — a LangGraph state machine generates code, executes it in the sandbox, and on failure feeds the actual error message back into the next generation attempt — looping until the code works or a max-attempt limit is reached.
7. **Test generation** — reuses the generate → execute → self-correct loop to write and validate pytest-style tests for a target function, retrieved via the same RAG pipeline as chat/explain.
8. **PR generation** — takes a fix, creates a git branch, commits and pushes it, then opens a real pull request via the GitHub API — verified end-to-end with a real merged PR.
9. **Frontend** — a React interface (Vite + Tailwind v4) with three modes (Chat, Explain, Find Bugs), grounded-response display with cited sources, and a live backend-connectivity indicator.

## Tech stack

- **Python**, **LangChain**, **LangGraph** — RAG pipeline + self-correcting agent loop
- **FastAPI** — backend API, CORS-enabled for the frontend
- **ChromaDB** — vector store
- **Docker** — isolated, safe code execution sandbox
- **Ollama** (`llama3.1`, `phi3`, `nomic-embed-text`) — local, free, offline inference
- **Claude API** — optional cloud backend, swappable via config
- **pylint / ast** — static analysis
- **GitPython + PyGithub** — repo cloning, branch/commit automation, PR creation
- **React + Vite + Tailwind CSS v4** — frontend

## Setup

```bash
# 1. Clone this repo
git clone https://github.com/Diveshanand08/AI-Software-Engineer.git
cd AI-Software-Engineer

# 2. Create and activate a virtual environment
python -m venv venv
.\venv\Scripts\Activate      # Windows
source venv/bin/activate      # Mac/Linux

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Install Ollama (https://ollama.com) and pull models
ollama pull llama3.1
ollama pull phi3
ollama pull nomic-embed-text

# 5. Install Docker Desktop (https://docker.com/products/docker-desktop)
#    Windows users: requires WSL2 (wsl --install, then restart)
docker pull python:3.11-slim

# 6. Add secrets to .env
#    ANTHROPIC_API_KEY=...   (optional, only if using Claude instead of Ollama)
#    GITHUB_TOKEN=...        (required for PR generation - needs 'repo' scope)

# 7. Set up the frontend
cd frontend
npm install
```

## Usage

**CLI:**
```bash
# Index a repo (local path or GitHub URL)
python indexer.py --local "C:\path\to\repo" --name my_repo
python indexer.py --repo https://github.com/psf/requests.git --name requests_test

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

# Open an automated PR with a fix
python pr_generator.py --repo "owner/repo" --file "path/in/repo.py" --fixed-code-file "local_fix.py" --title "Fix X" --description "..."
```

**API + Frontend:**
```bash
# Terminal 1 - backend
uvicorn api:app --reload --port 8000

# Terminal 2 - frontend
cd frontend
npm run dev
```
Open `http://localhost:5173`. Interactive API docs at `http://localhost:8000/docs`.

## Design decisions

- **AST-based chunking over fixed-size splitting** — preserves logical code boundaries (a full function stays together), meaningfully improving retrieval relevance.
- **Batched embedding** — large repos (800+ chunks) are embedded in batches of 50 rather than one giant request, avoiding overwhelming the local embedding server. Validated on a real 37-file, 817-chunk repo.
- **Model-agnostic backend** — the same LangChain interface swaps between local Ollama models (free, private, offline) and Claude's API (higher quality, paid) without touching core logic.
- **Grounded generation** — the system prompt forces the LLM to answer only from retrieved context and explicitly say when it doesn't have enough information, reducing hallucination risk.
- **Error-aware retries, not blind retries** — the self-correcting loop feeds the actual runtime error back into the next generation attempt, so the model fixes the real root cause instead of guessing again.
- **Sandbox-first safety** — no generated or analyzed code ever executes on the host machine; everything runs in a disposable, network-isolated, resource-capped container with a hard timeout.
- **git-based PR pipeline** — branch creation, commits, and pushes use plain git (proven reliable) rather than the GitHub API's git-refs endpoints, with the GitHub API used only for the final PR creation step, plus retry logic for its eventual-consistency lag right after a push.

## Known limitations

- Unit test generation is less reliable on functions with many internal dependencies (see note above).
- Local model inference (`llama3.1` especially) can take 1-3 minutes per response on CPU-only hardware — the UI surfaces an honest elapsed-time indicator rather than hiding this.
- PR creation occasionally requires a short retry due to GitHub API eventual-consistency delay immediately after a push; handled automatically with a 3-attempt retry.

## Roadmap

- [x] Docker sandbox for safe, isolated code execution
- [x] LangGraph self-correcting agent loop
- [x] Automated unit test generation (simple functions reliable; complex-function reliability in progress)
- [x] Automated pull request creation via GitHub API
- [x] React frontend with chat/explain/bugs interface & Google Sign-In
- [x] Persistent chat history across sessions (SQLite + user-specific Gmail isolation)

## Author

Built by Divesh as part of AI/LLM application engineering practice
