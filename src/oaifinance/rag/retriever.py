"""Dense retriever over the policy/contract corpus.

Uses sentence-transformers + in-memory cosine-similarity (via sklearn) so the
demo runs without FAISS wheels. For scale, swap in Databricks Vector Search
or FAISS; the contract is the same.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import polars as pl
from sklearn.metrics.pairwise import cosine_similarity

from oaifinance.config import SILVER_DIR
from oaifinance.rag import corpus as corpus_mod

EMBED_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@dataclass
class RetrievalHit:
    chunk_id: str
    doc_id: str
    doc_title: str
    section_title: str
    text: str
    score: float


class Retriever:
    def __init__(self, chunks: pl.DataFrame, embeddings: np.ndarray, model) -> None:
        self.chunks = chunks
        self.embeddings = embeddings
        self.model = model

    def search(self, query: str, top_k: int = 5) -> list[RetrievalHit]:
        q_vec = self.model.encode([query], normalize_embeddings=True)
        sims = cosine_similarity(q_vec, self.embeddings)[0]
        order = np.argsort(-sims)[:top_k]
        hits = []
        for idx in order:
            row = self.chunks.row(int(idx), named=True)
            hits.append(
                RetrievalHit(
                    chunk_id=row["chunk_id"],
                    doc_id=row["doc_id"],
                    doc_title=row["doc_title"],
                    section_title=row["section_title"],
                    text=row["text"],
                    score=float(sims[idx]),
                )
            )
        return hits


def build() -> Retriever:
    from sentence_transformers import SentenceTransformer

    chunks = corpus_mod.load()
    model = SentenceTransformer(EMBED_MODEL_NAME)
    embeddings = model.encode(
        chunks["text"].to_list(),
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)

    SILVER_DIR.mkdir(parents=True, exist_ok=True)
    np.save(SILVER_DIR / "corpus_embeddings.npy", embeddings)
    chunks.write_parquet(SILVER_DIR / "corpus_chunks.parquet")

    return Retriever(chunks, embeddings, model)


def load() -> Retriever:
    """Load a previously built retriever from disk."""
    from sentence_transformers import SentenceTransformer

    chunks = pl.read_parquet(SILVER_DIR / "corpus_chunks.parquet")
    embeddings = np.load(SILVER_DIR / "corpus_embeddings.npy")
    model = SentenceTransformer(EMBED_MODEL_NAME)
    return Retriever(chunks, embeddings, model)


if __name__ == "__main__":
    r = build()
    for q in [
        "NDC-HCPCS crosswalk mismatch",
        "billed amount exceeds ASP threshold",
        "prior authorization required for commercial oncology biologic",
    ]:
        print(f"\nquery: {q}")
        for hit in r.search(q, top_k=3):
            print(f"  {hit.score:.3f}  {hit.doc_id} §{hit.section_title}")
