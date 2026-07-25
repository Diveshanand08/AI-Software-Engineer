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

# --- config ---
CLONE_DIR = Path("./_cloned_repos")
CHROMA_DIR = Path("./chroma_db")
EMBED_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# file extensions worth indexing
CODE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs", ".cpp", ".c", ".h"}
IGNORE_DIRS = {".git", "node_modules", "venv", "__pycache__", ".venv", "dist", "build", "_cloned_repos", "chroma_db"}


def clone_repo(repo_url: str, dest_name: str) -> Path:
    """Clone a repo to CLONE_DIR/dest_name. Skips if already cloned."""
    target = CLONE_DIR / dest_name
    if target.exists():
        print(f"[indexer] Repo already cloned at {target}, skipping clone.")
        return target
    CLONE_DIR.mkdir(exist_ok=True)
    print(f"[indexer] Cloning {repo_url} into {target} ...")
    git.Repo.clone_from(repo_url, target, depth=1)
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


def collect_documents(repo_path: Path) -> list[Document]:
    """Walk repo, chunk all code files."""
    all_chunks = []
    file_count = 0

    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for fname in files:
            fpath = Path(root) / fname
            if fpath.suffix not in CODE_EXTENSIONS:
                continue
            file_count += 1
            if fpath.suffix == ".py":
                all_chunks.extend(chunk_python_file(fpath, repo_path))
            else:
                all_chunks.extend(chunk_file_whole(fpath, repo_path))

    print(f"[indexer] Scanned {file_count} code files, produced {len(all_chunks)} chunks.")
    return all_chunks


def build_index(documents: list[Document], collection_name: str):
    """Embed documents and persist into Chroma."""
    if not documents:
        print("[indexer] No documents to index. Aborting.")
        return

    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

    print(f"[indexer] Embedding {len(documents)} chunks with '{EMBED_MODEL}' ...")
    vectordb = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory=str(CHROMA_DIR),
    )
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