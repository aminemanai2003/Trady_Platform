"""
Faiss-based vector store for per-user ANN retrieval.

Builds an IndexFlatIP (inner-product = cosine on L2-normalised vectors) per user
and caches it in process memory.  Falls back gracefully to the NumPy path if
faiss is not installed.

Thread-safety: a per-user lock prevents concurrent rebuild races while still
allowing parallel queries for different users.
"""

import json
import logging
import threading
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Module-level cache ─────────────────────────────────────────────────────────
# {owner_email: (index | None, meta: list[dict])}
# None means the user has no chunks; "MISSING" sentinel means not yet built.
_indexes: Dict[str, Optional[Tuple]] = {}
_user_locks: Dict[str, threading.Lock] = {}
_global_lock = threading.Lock()


def _get_user_lock(owner_email: str) -> threading.Lock:
    with _global_lock:
        if owner_email not in _user_locks:
            _user_locks[owner_email] = threading.Lock()
        return _user_locks[owner_email]


# ── Helpers ────────────────────────────────────────────────────────────────────

def _l2_normalize(matrix: np.ndarray) -> np.ndarray:
    """Row-wise L2 normalisation. Avoids division by zero."""
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    return matrix / norms


def _try_import_faiss():
    try:
        import faiss  # noqa: PLC0415
        return faiss
    except ImportError:
        return None


# ── Public API ─────────────────────────────────────────────────────────────────

def build_user_index(owner_email: str) -> None:
    """
    Load all chunks for *owner_email* from the DB and build a Faiss IndexFlatIP.
    Uses GPU (device 0) if faiss-gpu is installed and a CUDA device is present,
    otherwise falls back to CPU.
    Stores result in the module-level cache.
    """
    from rag_tutor.models import DocumentChunk  # noqa: PLC0415 (avoid circular)

    faiss = _try_import_faiss()
    if faiss is None:
        logger.warning("faiss not installed — run: pip install faiss-cpu")
        with _get_user_lock(owner_email):
            _indexes[owner_email] = None
        return

    qs = (
        DocumentChunk.objects
        .filter(document__owner_email=owner_email)
        .select_related("document")
        .only("text", "embedding_json", "document__filename")
    )

    texts: List[str] = []
    filenames: List[str] = []
    vectors: List[List[float]] = []

    for chunk in qs:
        try:
            emb = json.loads(chunk.embedding_json)
            vectors.append(emb)
            texts.append(chunk.text)
            filenames.append(chunk.document.filename)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping malformed chunk %s: %s", chunk.id, exc)

    if not vectors:
        with _get_user_lock(owner_email):
            _indexes[owner_email] = None
        logger.debug("No chunks for %s — empty index stored", owner_email)
        return

    matrix = np.array(vectors, dtype=np.float32)
    matrix = _l2_normalize(matrix)
    dim = matrix.shape[1]

    index = faiss.IndexFlatIP(dim)

    # Attempt GPU acceleration
    try:
        num_gpus = faiss.get_num_gpus()
        if num_gpus > 0:
            res = faiss.StandardGpuResources()
            index = faiss.index_cpu_to_gpu(res, 0, index)
            logger.info("Faiss index on GPU:0 for %s (dim=%d, n=%d)", owner_email, dim, len(vectors))
    except Exception as exc:  # noqa: BLE001
        logger.debug("Faiss GPU not available (%s) — using CPU", exc)

    index.add(matrix)

    meta = [{"text": t, "document_filename": f} for t, f in zip(texts, filenames)]

    with _get_user_lock(owner_email):
        _indexes[owner_email] = (index, meta)

    logger.info(
        "Built Faiss index for %s — %d vectors, dim=%d",
        owner_email, len(vectors), dim,
    )


def invalidate_user_index(owner_email: str) -> None:
    """Remove the cached index for *owner_email*. Call after any upload or delete."""
    with _get_user_lock(owner_email):
        _indexes.pop(owner_email, None)
    logger.debug("Invalidated Faiss index for %s", owner_email)


def search_user_index(
    owner_email: str,
    query_embedding: list,
    top_k: int = 5,
    min_score: float = 0.20,
) -> list:
    """
    Return up to *top_k* chunks whose cosine similarity >= *min_score*.
    Builds (and caches) the index on first call.

    Return shape matches ``vector_store.retrieve_top_chunks()``:
        [{"text": str, "score": float, "document_filename": str}, ...]
    """
    # Lazy build
    if owner_email not in _indexes:
        build_user_index(owner_email)

    entry = _indexes.get(owner_email)
    if entry is None:
        return []

    faiss = _try_import_faiss()
    if faiss is None:
        return []

    index, meta = entry

    q = np.array([query_embedding], dtype=np.float32)
    q = _l2_normalize(q)

    k = min(top_k, len(meta))
    scores, indices = index.search(q, k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        if float(score) < min_score:
            continue
        results.append({
            "text":              meta[idx]["text"],
            "score":             round(float(score), 4),
            "document_filename": meta[idx]["document_filename"],
        })

    logger.info(
        "Faiss search: %d/%d results for %s (best=%.3f)",
        len(results), len(meta), owner_email,
        results[0]["score"] if results else 0.0,
    )
    return results
