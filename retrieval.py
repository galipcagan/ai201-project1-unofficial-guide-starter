"""
retrieval.py — Milestone 4: embedding + retrieval.

Pipeline stages implemented here (see planning.md > Architecture):
    3. Embedding + Vector Store -> build_index()
    4. Retrieval                -> retrieve()

Embedding model : all-MiniLM-L6-v2 (sentence-transformers, 384-dim, local, no API key)
Vector store    : ChromaDB (PersistentClient, cosine distance)
Top-k default   : 5  (per planning.md > Retrieval Approach)

Run:
    python retrieval.py            # builds the index, then runs the eval queries
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# --- Configuration (mirrors planning.md > Retrieval Approach) ----------------
CHUNKS_FILE = Path(__file__).parent / "chunks.json"
CHROMA_DIR = Path(__file__).parent / "chroma_db"
COLLECTION_NAME = "binghamton_cs_reviews"
EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
DEFAULT_K = 5

_model: SentenceTransformer | None = None


def get_model() -> SentenceTransformer:
    """Load the embedding model once and cache it (first call downloads ~80MB)."""
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL_NAME)
    return _model


def _client() -> chromadb.api.ClientAPI:
    # PersistentClient writes the vector store to disk so we don't re-embed every run.
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def build_index(force: bool = True) -> chromadb.api.models.Collection.Collection:
    """Embed every chunk in chunks.json and store it in ChromaDB with metadata.

    Metadata stored per chunk includes the source document name (`source_file`)
    and the chunk's position within that document (`chunk_index`) — both needed
    for attribution and debugging later.
    """
    chunks = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    client = _client()

    if force:
        # Drop any existing collection so a re-run doesn't create duplicates.
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass

    # hnsw:space=cosine -> query distances are cosine distances (~0 = identical).
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    if collection.count() == len(chunks) and not force:
        return collection  # already built

    model = get_model()
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(
        texts, normalize_embeddings=True, show_progress_bar=False
    ).tolist()

    # Assign each chunk its position within its own source document.
    per_doc_counter: dict[str, int] = {}
    ids, metadatas = [], []
    for c in chunks:
        src = c["metadata"].get("source_file", "unknown")
        pos = per_doc_counter.get(src, 0)
        per_doc_counter[src] = pos + 1

        meta = {k: ("" if v is None else v) for k, v in c["metadata"].items()}
        meta["chunk_index"] = pos  # position of this chunk within its document
        metadatas.append(meta)
        ids.append(f"{src}::{pos}")

    collection.add(ids=ids, documents=texts, embeddings=embeddings, metadatas=metadatas)
    return collection


def retrieve(query: str, k: int = DEFAULT_K) -> list[dict]:
    """Return the top-k most relevant chunks for `query`.

    Each result: {text, distance, source_file, chunk_index, source_url, metadata}.
    Lower distance = more similar (cosine distance, ~0 identical, >0.6 weak match).
    """
    collection = _client().get_collection(COLLECTION_NAME)
    query_emb = get_model().encode([query], normalize_embeddings=True).tolist()
    res = collection.query(
        query_embeddings=query_emb,
        n_results=k,
        include=["documents", "metadatas", "distances"],
    )
    results = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        results.append({
            "text": doc,
            "distance": dist,
            "source_file": meta.get("source_file", ""),
            "chunk_index": meta.get("chunk_index", ""),
            "source_url": meta.get("source_url", ""),
            "metadata": meta,
        })
    return results


# --- Driver: build the index and sanity-check retrieval ----------------------
# Three of the five evaluation-plan queries from planning.md.
EVAL_QUERIES = [
    "What do students say about Patrick Madden's lectures and exams?",
    "Is Thomas Bartenstein a good professor to take for CS 220?",
    "Which CS professor has the highest student ratings and an easy class?",
]


def _demo() -> None:
    try:
        import sys
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    print(f"Embedding model: {EMBED_MODEL_NAME}")
    collection = build_index(force=True)
    print(f"Indexed {collection.count()} chunks into ChromaDB collection "
          f"'{COLLECTION_NAME}' (cosine distance)\n")

    for q in EVAL_QUERIES:
        print("=" * 78)
        print(f"QUERY: {q}")
        print("=" * 78)
        for rank, r in enumerate(retrieve(q, k=DEFAULT_K), 1):
            print(f"\n[{rank}] distance={r['distance']:.3f}  "
                  f"source={r['source_file']}  pos={r['chunk_index']}")
            print("    " + r["text"].replace("\n", "\n    "))
        print()


if __name__ == "__main__":
    _demo()
