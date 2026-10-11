"""
indexer.py
Clones a GitHub repo, chunks its code files (function/class level for Python,
file-level fallback for other languages), and embeds the chunks into a local
Chroma vector store using Ollama's nomic-embed-text model.

Usage:
    python indexer.py --repo https://github.com/user/repo.git --name my_repo
    python indexer.py --local /path/to/existing/repo --name my_repo
"""

import argparse
import ast
import os
import shutil
from pathlib import Path

import git
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

class GeminiCloudEmbeddings(Embeddings):
    """Zero-memory cloud embeddings using Gemini's API with rate-limit retry."""
    def __init__(self):
        from openai import OpenAI
        self._client = OpenAI(
            api_key=os.getenv("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self._model = "models/gemini-embedding-001"

    def embed_documents(self, texts):
        import time
        results = []
        for i in range(0, len(texts), 50):
            chunk = texts[i : i + 50]
            for attempt in range(5):
                try:
                    resp = self._client.embeddings.create(input=chunk, model=self._model)
                    results.extend([item.embedding for item in resp.data])
                    time.sleep(0.5)
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < 4:
                        print(f"[indexer] Rate limit 429 encountered. Backing off for {(attempt + 1) * 6}s...")
                        time.sleep((attempt + 1) * 6)
                    else:
                        raise e
        return results

    def embed_query(self, text):
        import time
        for attempt in range(5):
            try:
                resp = self._client.embeddings.create(input=[text], model=self._model)
                return resp.data[0].embedding
            except Exception as e:
                if "429" in str(e) and attempt < 4:
                    time.sleep((attempt + 1) * 3)
                else:
                    raise e
        return []

class LocalDefaultEmbeddings(Embeddings):
    """Fallback embedding model using Chroma's built-in ONNX all-MiniLM-L6-v2 model with micro-batching for ultra-low RAM."""
    def __init__(self):
        import chromadb.utils.embedding_functions as ef
        self._fn = ef.DefaultEmbeddingFunction()

    def embed_documents(self, texts):
        results = []
        for i in range(0, len(texts), 10):
            sub = texts[i : i + 10]
            results.extend([list(map(float, v)) for v in self._fn(sub)])
        return results

    def embed_query(self, text):
        return list(map(float, self._fn([text])[0]))

def get_embedding_function():
    """Return OllamaEmbeddings if running locally, otherwise LocalDefaultEmbeddings (zero API quota/rate limits)."""
    try:
        import urllib.request
        urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/version", timeout=1)
        return OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
    except Exception:
        pass

    return LocalDefaultEmbeddings()

# --- config ---
CLONE_DIR = Path(os.getenv("CLONE_DIR", "./_cloned_repos"))
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", "./chroma_db"))
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

# file extensions worth indexing
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h"}
IGNORE_DIRS = {
    ".git", "node_modules", "venv", "__pycache__", ".venv", "dist", "build",
    "_cloned_repos", "chroma_db", ".next", "out", ".output", ".cache",
    "coverage", ".turbo", ".nuxt", ".svelte-kit", ".docusaurus", "vendor",
    ".yarn", ".pnpm-store", ".idea", ".vscode"
}


def clone_repo(repo_url: str, dest_name: str) -> Path:
    """Clone a repo to CLONE_DIR/dest_name. Skips if already cloned."""
    target = CLONE_DIR / dest_name
    if target.exists():
        print(f"[indexer] Repo already cloned at {target}, skipping clone.")
        return target
    CLONE_DIR.mkdir(exist_ok=True)
    print(f"[indexer] Cloning {repo_url} into {target} ...")
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    try:
        git.Repo.clone_from(repo_url, target, depth=1, env=env)
    except Exception as e:
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        raise e
    print("[indexer] Clone complete.")
    return target


def chunk_python_file(filepath: Path, repo_root: Path) -> list[Document]:
    """Chunk a Python file into function/class-level pieces using ast."""
    chunks = []
    try:
        source = filepath.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        # fall back to whole-file chunk if parsing fails
        return chunk_file_whole(filepath, repo_root)

    lines = source.splitlines()
    rel_path = filepath.relative_to(repo_root)

    top_level_nodes = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]

    if not top_level_nodes:
        return chunk_file_whole(filepath, repo_root)

    for node in top_level_nodes:
        start = node.lineno - 1
        end = getattr(node, "end_lineno", start + 1)
        snippet = "\n".join(lines[start:end])
        if not snippet.strip():
            continue
        chunks.append(
            Document(
                page_content=snippet,
                metadata={
                    "file": str(rel_path),
                    "name": node.name,
                    "type": type(node).__name__,
                    "start_line": start + 1,
                    "end_line": end,
                },
            )
        )
    return chunks


def chunk_file_whole(filepath: Path, repo_root: Path, max_chars: int = 3000) -> list[Document]:
    """Fallback chunker for non-Python files: split by size."""
    rel_path = filepath.relative_to(repo_root)
    try:
        text = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return []

    chunks = []
    for i in range(0, len(text), max_chars):
        piece = text[i : i + max_chars]
        if not piece.strip():
            continue
        chunks.append(
            Document(
                page_content=piece,
                metadata={
                    "file": str(rel_path),
                    "name": rel_path.name,
                    "type": "file_slice",
                    "start_line": None,
                    "end_line": None,
                },
            )
        )
    return chunks


def collect_documents(repo_path: Path, max_chunks: int = 800) -> list[Document]:
    """Walk repo, chunk all code files while skipping minified/compiled files."""
    all_chunks = []
    file_count = 0

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix not in CODE_EXTENSIONS:
                continue
            lower_name = fname.lower()
            if lower_name.endswith(".min.js") or lower_name.endswith(".bundle.js") or lower_name.endswith(".d.ts") or lower_name.endswith(".min.css"):
                continue

            file_count += 1
            if fpath.suffix == ".py":
                all_chunks.extend(chunk_python_file(fpath, repo_path))
            else:
                all_chunks.extend(chunk_file_whole(fpath, repo_path))

            if len(all_chunks) >= max_chunks:
                print(f"[indexer] Reached chunk limit ({max_chunks}). Capping collection for cloud performance.")
                all_chunks = all_chunks[:max_chunks]
                break
        if len(all_chunks) >= max_chunks:
            break

    print(f"[indexer] Scanned {file_count} code files, produced {len(all_chunks)} chunks.")
    return all_chunks


def build_index(documents: list[Document], collection_name: str, batch_size: int = 20, progress_callback=None):
    """Embed documents and persist into Chroma, reporting progress via callback."""
    if not documents:
        print("[indexer] No documents to index. Aborting.")
        return

    embeddings = get_embedding_function()
    total = len(documents)
    print(f"[indexer] Embedding {total} chunks in batches of {batch_size} ...")

    vectordb = None
    for i in range(0, total, batch_size):
        batch = documents[i : i + batch_size]
        current_count = min(i + len(batch), total)
        percent = int(current_count / total * 100)
        msg = f"Embedding chunks: {current_count}/{total} ({percent}%)..."
        print(f"[indexer]   {msg}")
        if progress_callback:
            try:
                progress_callback(msg)
            except Exception:
                pass

        if vectordb is None:
            vectordb = Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                collection_name=collection_name,
                persist_directory=str(CHROMA_DIR),
            )
        else:
            vectordb.add_documents(batch)

    print(f"[indexer] Done. Index persisted to {CHROMA_DIR} under collection '{collection_name}'.")
    return vectordb


def main():
    parser = argparse.ArgumentParser(description="Index a code repo into Chroma.")
    parser.add_argument("--repo", help="Git URL to clone")
    parser.add_argument("--local", help="Path to an already-local repo (skips cloning)")
    parser.add_argument("--name", required=True, help="Name for this index/collection")
    args = parser.parse_args()

    if not args.repo and not args.local:
        raise SystemExit("Provide either --repo <git-url> or --local <path>")

    if args.local:
        repo_path = Path(args.local).resolve()
    else:
        repo_path = clone_repo(args.repo, args.name)

    documents = collect_documents(repo_path)

    # quick sanity preview
    print("\n[indexer] Sample chunks:")
    for doc in documents[:3]:
        preview = doc.page_content[:120].replace("\n", " ")
        print(f"  - {doc.metadata['file']} :: {doc.metadata['name']} -> {preview}...")

    build_index(documents, collection_name=args.name)


if __name__ == "__main__":
    main()