"""
Vector store — retrieval using Faiss (primary) or NumPy cosine (fallback).

Embeddings are stored as JSON text in the DB.
At query time we delegate to ``faiss_store`` which keeps per-user ANN indexes
in process memory.  If faiss is not installed, falls back to the original
NumPy brute-force loop so the system stays functional without GPU deps.

Strictly filtered by owner_email to prevent cross-user data leaks.
"""

import json
import logging

import numpy as np

logger = logging.getLogger(__name__)


# ── NumPy fallback ─────────────────────────────────────────────────────────────

def _cosine(a: list, b: list) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb)) / denom


def _retrieve_numpy(
    query_embedding: list,
    owner_email: str,
    top_k: int,
    min_score: float,
) -> list:
    from rag_tutor.models import DocumentChunk  # noqa: PLC0415

    chunks = (
        DocumentChunk.objects
        .filter(document__owner_email=owner_email)
        .select_related("document")
        .only("text", "embedding_json", "document__filename")
    )

    if not chunks.exists():
        return []

    scored: list = []
    for chunk in chunks:
        try:
            emb   = json.loads(chunk.embedding_json)
            score = _cosine(query_embedding, emb)
            scored.append((score, chunk.text, chunk.document.filename))
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping malformed chunk %s: %s", chunk.id, exc)

    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        {
            "text":              text,
            "score":             round(score, 4),
            "document_filename": filename,
        }
        for score, text, filename in scored[:top_k]
        if score >= min_score
    ]


# ── Public API ─────────────────────────────────────────────────────────────────

def retrieve_top_chunks(
    query_embedding: list,
    owner_email: str,
    top_k: int = 5,
    min_score: float = 0.20,
) -> list:
    """
    Return the top-k most similar document chunks for owner_email.

    Tries Faiss first (fast ANN, optional GPU), falls back to NumPy.
    Each result: {"text": str, "score": float, "document_filename": str}

    Strictly filtered by owner_email — no cross-user data is ever returned.
    """
    try:
        from .faiss_store import search_user_index  # noqa: PLC0415
        results = search_user_index(
            owner_email, query_embedding, top_k=top_k, min_score=min_score
        )
        logger.info(
            "Faiss retrieved %d chunks for %s (best=%.3f)",
            len(results), owner_email,
            results[0]["score"] if results else 0.0,
        )
        return results
    except Exception as exc:  # noqa: BLE001
        logger.warning("Faiss search failed (%s) — falling back to NumPy", exc)

    # NumPy fallback
    results = _retrieve_numpy(query_embedding, owner_email, top_k, min_score)
    logger.info(
        "NumPy retrieved %d chunks for %s (best=%.3f)",
        len(results), owner_email,
        results[0]["score"] if results else 0.0,
    )
    return results
