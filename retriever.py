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

from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma

CHROMA_DIR = Path("./chroma_db")
EMBED_MODEL = "nomic-embed-text"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def load_retriever(collection_name: str, k: int = 4):
    """Load the persisted Chroma collection and return a retriever object."""
    embeddings = OllamaEmbeddings(model=EMBED_MODEL, base_url=OLLAMA_BASE_URL)

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


def retrieve(collection_name: str, query: str, k: int = 4):
    """Run a query against the index, return a list of (content, metadata) results."""
    retriever = load_retriever(collection_name, k=k)
    results = retriever.invoke(query)

    formatted = []
    for doc in results:
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