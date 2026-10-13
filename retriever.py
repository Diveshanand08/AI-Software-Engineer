"""
retriever.py
Loads the persisted Chroma index built by indexer.py and lets you query it
for the most relevant code chunks. Uses the same Ollama embedding model
as the indexer (embeddings must match between indexing and querying).

Usage (standalone test):
    python retriever.py --name test_repo --query "how does the indexer chunk python files"
"""

import argparse
import os
from pathlib import Path

from langchain_chroma import Chroma
from indexer import get_embedding_function

from core.config import settings

CHROMA_DIR = settings.CHROMA_DIR
EMBED_MODEL = settings.EMBED_MODEL
OLLAMA_BASE_URL = settings.OLLAMA_BASE_URL


def get_embeddings_for_collection(collection_name: str):
    """Dynamically match embedding function to collection's existing dimension to prevent InvalidArgumentError."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        c = client.get_collection(collection_name)
        sample = c.get(limit=1, include=["embeddings"])
        embs = sample.get("embeddings")
        if embs is not None and len(embs) > 0 and len(embs[0]) > 0:
            dim = len(embs[0])
            if dim == 768:
                from langchain_ollama import OllamaEmbeddings
                return OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)
            elif dim == 384:
                from indexer import LocalDefaultEmbeddings
                return LocalDefaultEmbeddings()
            elif dim == 3072:
                from indexer import GeminiCloudEmbeddings
                return GeminiCloudEmbeddings()
    except Exception:
        pass
    return get_embedding_function()


def load_retriever(collection_name: str, k: int = 4):
    """Load the persisted Chroma collection and return a retriever object."""
    embeddings = get_embeddings_for_collection(collection_name)

    vectordb = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DIR),
    )

    count = vectordb._collection.count()
    if count == 0:
        raise ValueError(
            f"Collection '{collection_name}' is empty. "
            f"Did you run indexer.py with --name {collection_name} first?"
        )

    return vectordb.as_retriever(search_kwargs={"k": k})


def is_broad_query(query: str) -> bool:
    """Check if query is general/architectural rather than targeting a specific function."""
    q = query.lower().strip()
    broad_keywords = [
        "explain the code", "explain code", "explain the project", "explain this repo",
        "what does this do", "what does this project do", "what does this code do",
        "overview", "architecture", "structure", "summary", "summarize",
        "how does this work", "how does the project work", "how does it work",
        "walk me through", "introduce", "tell me about this", "what is this repo"
    ]
    if len(q.split()) <= 4 and any(w in q for w in ["explain", "code", "repo", "project", "work", "what", "how", "all"]):
        return True
    return any(bk in q for bk in broad_keywords)


def retrieve(collection_name: str, query: str, k: int = 6):
    """Run a query against the index, return a list of (content, metadata) results.
    
    If query is broad or general, automatically expands search to include architecture/overview
    and increases k to provide comprehensive context.
    """
    broad = is_broad_query(query)
    effective_k = max(k, 8) if broad else k

    retriever = load_retriever(collection_name, k=effective_k)
    raw_results = retriever.invoke(query)

    if broad:
        try:
            extra = retriever.invoke("overview architecture main entrypoint workflow summary")
            raw_results.extend(extra)
        except Exception:
            pass

    # Deduplicate while preserving rank order
    seen = set()
    formatted = []
    for doc in raw_results:
        key = (doc.metadata.get("file"), doc.metadata.get("name"), doc.metadata.get("start_line"))
        if key in seen:
            continue
        seen.add(key)
        formatted.append(
            {
                "content": doc.page_content,
                "file": doc.metadata.get("file"),
                "name": doc.metadata.get("name"),
                "type": doc.metadata.get("type"),
                "start_line": doc.metadata.get("start_line"),
                "end_line": doc.metadata.get("end_line"),
            }
        )
        if len(formatted) >= effective_k:
            break

    return formatted


def format_for_prompt(results: list[dict]) -> str:
    """Turn retrieved chunks into a clean context block for an LLM prompt."""
    blocks = []
    for r in results:
        location = f"{r['file']}"
        if r["start_line"]:
            location += f" (lines {r['start_line']}-{r['end_line']})"
        blocks.append(f"# {location} :: {r['name']} [{r['type']}]\n{r['content']}")
    return "\n\n---\n\n".join(blocks)


def main():
    parser = argparse.ArgumentParser(description="Query a Chroma code index.")
    parser.add_argument("--name", required=True, help="Collection name used during indexing")
    parser.add_argument("--query", required=True, help="Natural language query")
    parser.add_argument("--k", type=int, default=4, help="Number of chunks to retrieve")
    args = parser.parse_args()

    results = retrieve(args.name, args.query, k=args.k)

    print(f"\n[retriever] Top {len(results)} results for: '{args.query}'\n")
    for i, r in enumerate(results, 1):
        loc = f"{r['file']}"
        if r["start_line"]:
            loc += f" (lines {r['start_line']}-{r['end_line']})"
        print(f"--- Result {i}: {r['name']} [{r['type']}] :: {loc} ---")
        preview = r["content"][:300]
        print(preview)
        print()


if __name__ == "__main__":
    main()