# AI Software Engineer — Autonomous Code Assistant

A full-stack AI code assistant that indexes GitHub repositories and lets you chat with, understand, and debug a codebase using retrieval-augmented generation (RAG) — running entirely on local, open-source models via Ollama (or swappable to Claude's API).

## Features

| Feature | Status |
|---|---|
| Repo indexing (AST-based chunking + vector embeddings) |  Done |
| Chat with your codebase (RAG Q&A) |  Done |
| Explain functions/classes (structured breakdown) |  Done |
| Automated bug detection (static analysis + LLM reasoning) |  Done |
| FastAPI backend (HTTP API for all features) |  Done |
| Docker sandbox for safe code execution |  In progress |
| Self-correcting fix generation (LangGraph agent loop) |  In progress |
| Automated unit test generation |  In progress |
| Pull request generation (GitHub API) |  In progress |
| Web frontend (React) with chat history |  In progress |
| Code quality metrics dashboard |  Planned |

## Architecture

```
                 ┌──────────────┐
                 │   FastAPI     │
                 │   Backend     │
                 └──────┬───────┘
                        │
        ┌───────────────┼────────────────┐
        │               │                │
  ┌─────▼─────┐   ┌─────▼─────┐   ┌──────▼──────┐
  │  Indexer   │   │   Chat/    │   │ Bug Finder  │
  │ (AST +     │   │  Explain   │   │ (pylint +   │
  │  Chroma)   │   │  (RAG)     │   │  LLM)       │
  └─────┬─────┘   └─────┬─────┘   └──────┬──────┘
        │               │                │
        └───────────────┼────────────────┘
                        │
                 ┌──────▼───────┐
                 │  ChromaDB     │
                 │ Vector Store  │
                 └──────┬───────┘
                        │
                 ┌──────▼───────┐
                 │    Ollama     │
                 │ (llama3.1 /   │
                 │  phi3 / Claude)│
                 └───────────────┘
```

## How it works

1. **Indexing** — clones a repo (or reads a local path), parses Python files with the `ast` module to chunk code at function/class boundaries (not naive fixed-size splitting), and embeds each chunk into a local ChromaDB vector store using Ollama's `nomic-embed-text` model.
2. **Retrieval** — a natural-language query is embedded the same way, and the top-k most similar code chunks are retrieved from the vector store.
3. **Generation** — retrieved chunks + the user's question are sent to a local LLM (`llama3.1` / `phi3`) or Claude's API, grounded strictly in the retrieved context to minimize hallucination. Every answer cites its source file and function name.
4. **Bug detection** — runs `pylint` static analysis on a target file, then uses the LLM to separate real logic/security issues from style noise, explaining *why* each real issue matters and suggesting a fix.

## Tech stack

- **Python**, **LangChain**, **LangGraph** (for the agent loop, in progress)
- **FastAPI** — backend API
- **ChromaDB** — vector store
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

# 5. (Optional) add ANTHROPIC_API_KEY to .env if using Claude instead of Ollama
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
```

**API:**
```bash
uvicorn api:app --reload --port 8000
# Interactive docs: http://localhost:8000/docs
```

## Example output

```
You: How does the chunk_python_file function work?

Assistant: The chunk_python_file function parses a Python file into an
Abstract Syntax Tree (AST) and extracts function/class-level chunks...
[full step-by-step breakdown, grounded in actual source]

Sources:
  - indexer.py :: chunk_python_file
  - indexer.py :: chunk_file_whole
```

## Design decisions

- **AST-based chunking over fixed-size splitting** — preserves logical code boundaries (a full function stays together), which meaningfully improves retrieval relevance for code Q&A.
- **Model-agnostic backend** — same LangChain interface swaps between local Ollama models (free, private, offline) and Claude's API (higher quality, paid) without touching core logic.
- **Grounded generation** — the system prompt forces the LLM to answer only from retrieved context and explicitly say when it doesn't have enough information, reducing hallucination risk on code-specific questions.

## Roadmap

- [ ] Docker sandbox for safe, isolated code execution
- [ ] LangGraph self-correcting agent loop: generate → execute → catch errors → fix → retry
- [ ] Automated unit test generation
- [ ] Automated pull request creation via GitHub API
- [ ] React frontend with persistent chat history
- [ ] Code quality metrics dashboard

## Author

Built by Divesh as part of AI/LLM application engineering practice, alongside adversarial ML security research on LoRA adapter vulnerabilities.
