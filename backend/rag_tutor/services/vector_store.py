"""
Vector store — cosine-similarity retrieval using NumPy.

Embeddings are stored as JSON text in PostgreSQL.
At query time we load all chunks for the given user and rank them
by cosine similarity. Strictly filtered by owner_email to prevent
cross-user data leaks.
"""

import json
import logging

import numpy as np

logger = logging.getLogger(__name__)


def _cosine(a: list, b: list) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom == 0.0:
        return 0.0
    return float(np.dot(va, vb)) / denom


def retrieve_top_chunks(
    query_embedding: list,
    owner_email: str,
    top_k: int = 5,
    min_score: float = 0.20,
) -> list:
    """
    Return the top-k most similar document chunks for owner_email.

    Each result: {"text": str, "score": float, "document_filename": str}

    Strictly filtered by owner_email — no cross-user data is ever returned.
    """
    # Import here to avoid module-level circular imports
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

    results = [
        {
            "text":              text,
            "score":             round(score, 4),
            "document_filename": filename,
        }
        for score, text, filename in scored[:top_k]
        if score >= min_score
    ]

    logger.info(
        "Retrieved %d/%d chunks for %s (best=%.3f)",
        len(results), len(scored), owner_email,
        results[0]["score"] if results else 0.0,
    )
    return results
