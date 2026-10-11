# System Architecture & Technical Documentation

The **AI Software Engineer Assistant** is a full-stack, RAG-powered engineering copilot designed to clone, analyze, index, and reason across entire codebases. It provides real-time streaming chat, structured AST function explanations, automated bug detection, sandbox-verified unit test generation, and automated GitHub Pull Request creation.

---

## 1. High-Level Architecture Overview

```
┌────────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER (React)                       │
│  Vite + React 18 + TailwindCSS + Lucide Icons + Google OAuth           │
│                                                                        │
│  [Header] ── [Sidebar] ── [ChatPanel] ── [CommandInput] ── [PRModal]   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / SSE Streaming
┌───────────────────────────────────▼────────────────────────────────────┐
│                         API GATEWAY LAYER (FastAPI)                    │
│                                                                        │
│  Routers:                                                              │
│   ├── /sessions    : Chat session history & persistence                │
│   ├── /index       : Asynchronous Git clone & AST ChromaDB indexer     │
│   ├── /ask & /explain : Streaming code reasoning with SSE              │
│   └── /code_ops    : Bug audits, auto-coder agent, tests, PR creator   │
└───────────────┬───────────────────┬───────────────────┬────────────────┘
                │                   │                   │
┌───────────────▼────────┐ ┌────────▼────────┐ ┌────────▼────────┐
│      RAG ENGINE        │ │   AGENT & DOCKER │ │   PERSISTENCE   │
│  • ChromaDB            │ │  • LangGraph     │ │  • SQLite (WAL) │
│  • AST Parser          │ │  • Docker Sandbox│ │  • chat_history │
│  • MiniLM / ONNX       │ │  • Pytest Runner │ │  • index_tasks  │
│  • Semantic Expander   │ │  • GitHub API    │ │                 │
└────────────────────────┘ └──────────────────┘ └─────────────────┘
```

---

## 2. Directory Structure

```
AI-Software-Engineer/
├── core/                       # Core system infrastructure
│   ├── config.py               # Centralized configuration & environment loader
│   ├── database.py             # Thread-safe SQLite persistence layer
│   └── exceptions.py           # Domain exceptions with HTTP status mappings
│
├── schemas/                    # Pydantic data contracts
│   ├── chat.py                 # Request/response schemas for Q&A, explain, agent, bugs
│   ├── indexing.py             # Schemas for repository indexing & status tracking
│   └── sessions.py             # Schemas for session & message history
│
├── routers/                    # Scalable FastAPI API endpoints
│   ├── sessions.py             # Session management & history endpoints
│   ├── indexing.py             # Git clone & ChromaDB vector indexing endpoints
│   ├── chat.py                 # Streaming Q&A & function explanation endpoints
│   └── code_ops.py             # Bug detection, auto-coder, pytest, & GitHub PR routes
│
├── services/                   # Business logic & automation engines
│   ├── code_agent.py           # LangGraph self-correcting auto-coder agent
│   ├── bug_finder.py           # AST static analysis & security auditor
│   ├── test_generator.py       # Sandbox-tested pytest generator
│   └── pr_generator.py         # Automated branch creation & GitHub PR submission
│
├── frontend/                   # React web application
│   ├── src/
│   │   ├── config/             # Client environment & constants
│   │   │   └── env.js          # API_BASE & OAuth configuration
│   │   ├── services/           # Network transport layer
│   │   │   └── api.js          # Client-side API caller isolating fetch logic
│   │   ├── hooks/              # Custom domain React hooks
│   │   │   ├── useIndexing.js  # Background clone polling & collection state
│   │   │   └── useChatSessions.js # Chat history & message state management
│   │   ├── components/         # Modular UI components
│   │   │   ├── layout/Header.jsx # Top navigation bar
│   │   │   ├── modals/PRModal.jsx # GitHub Pull Request modal
│   │   │   └── codeassist/     # Chat, Sidebar, CommandInput, ModelPicker
│   │   └── App.jsx             # Clean declarative app orchestrator
│
├── api.py                      # FastAPI application entrypoint
├── indexer.py                  # Code AST parser & vector embedding CLI/service
├── retriever.py                # Smart query expansion & Chroma vector retrieval
├── llm.py                      # Multi-provider LLM abstraction (Ollama, Groq, Gemini)
├── sandbox.py                  # Isolated Docker container runner
└── render.yaml                 # Infrastructure as Code specification for Render deployment
```

---

## 3. Core Subsystems

### A. RAG & Semantic Code Indexer
1. **Repository Ingestion:** Clones public GitHub repositories using shallow depth (`--depth 1`) with a 10-minute network speed buffer.
2. **AST-Driven Semantic Chunking:**
   - Python files are parsed using Python's `ast` module into function-level, class-level, and top-level module docstrings.
   - Non-Python files (JS, TS, Go, Rust, HTML, CSS, SQL, etc.) are chunked through size-aware chunking.
3. **Local ONNX Embeddings:** Utilizes ChromaDB's local `all-MiniLM-L6-v2` embedding engine with 10-chunk micro-batching (~9 MB peak RAM), eliminating 512MB RAM OOM crashes on Render without consuming external API quotas.
4. **Smart Hybrid Query Expansion:** Detects high-level queries (`"explain the code"`, `"overview"`, `"architecture"`) and automatically retrieves architectural entry points (`README.md`, `api.py`, `indexer.py`) while scaling to 8 diverse chunks.

### B. Self-Correcting Auto-Coder Agent
1. **LangGraph State Graph:** Orchestrates a generate-and-execute feedback loop.
2. **Docker Sandbox Verification:**
   - Network disabled (`network_disabled=True`).
   - Capped memory (`256MB`) and CPU (`0.5 cores`).
   - Hard execution timeout (`10s`).
3. **Error Feedback Loop:** Any execution failure or stack trace is fed back into the LLM prompt to self-correct up to $N$ attempts.

### C. Persistent Session History
- Stored in SQLite (`chat_history.db`) using **WAL (Write-Ahead Logging)** mode and 5,000ms busy timeout to prevent database locks.
- Messages stream in real-time to the browser via SSE and are atomically saved upon completion.

---

## 4. Environment Variables Reference

| Variable | Description | Default |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API Key | None |
| `GROQ_API_KEY` | Groq Cloud API Key | None |
| `GITHUB_TOKEN` | GitHub Personal Access Token (repo scope) | None |
| `OLLAMA_BASE_URL` | Local Ollama endpoint | `http://127.0.0.1:11434` |
| `DEFAULT_OLLAMA_MODEL` | Default model for local Ollama | `phi3` |
| `CHROMA_DIR` | ChromaDB persistence folder | `./chroma_db` |
| `CLONE_DIR` | Cloned repositories cache | `./_cloned_repos` |
| `DB_PATH` | SQLite database file location | `./chat_history.db` |
| `MAX_CHUNKS_PER_REPO` | Upper limit for indexed chunks | `800` |
