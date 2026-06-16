"""
Face embedding comparison and verification.

Similarity metric: cosine distance
  distance = 1 - cosine_similarity, range [0, 2]
  0 = identical vectors; 2 = perfectly opposite

Threshold:
  Default 0.40 — works well across both 128-d (face_recognition) and
  512-d (facenet-pytorch) embeddings because cosine distance is scale-invariant.
  Override with FACE_SIMILARITY_THRESHOLD env var.
"""

import logging
import os

import numpy as np

logger = logging.getLogger(__name__)

_DEFAULT_THRESHOLD = 0.40


# ── Distance metrics ──────────────────────────────────────────────────────────

def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cosine distance in [0, 2].  0 = identical; 2 = opposite.
    Lower is better (more similar).
    """
    a = np.array(a, dtype=np.float64)
    b = np.array(b, dtype=np.float64)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0.0 or norm_b == 0.0:
        return 2.0
    return float(1.0 - np.dot(a, b) / (norm_a * norm_b))


def euclidean_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Euclidean (L2) distance.  0 = identical."""
    return float(np.linalg.norm(np.array(a, dtype=np.float64) - np.array(b, dtype=np.float64)))


# ── Verification ──────────────────────────────────────────────────────────────

def verify(stored_embedding: list, live_embedding: np.ndarray) -> dict:
    """
    Compare a stored enrollment embedding against a freshly captured embedding.

    Args:
        stored_embedding: Decrypted list of floats from the database.
        live_embedding:   numpy array returned by extract_embedding().

    Returns:
        {
            "verified":   bool,
            "confidence": float,   # 0.0 (no match) → 1.0 (perfect match)
            "distance":   float,   # raw cosine distance
            "reason":     "match" | "no_match",
        }
    """
    threshold = float(os.getenv("FACE_SIMILARITY_THRESHOLD", str(_DEFAULT_THRESHOLD)))

    stored = np.array(stored_embedding, dtype=np.float64)
    live   = np.array(live_embedding,   dtype=np.float64)

    dist = cosine_distance(stored, live)

    # Map distance to a 0→1 confidence score.
    # confidence = 1 at dist=0; confidence = 0 at dist = threshold*2
    confidence = max(0.0, min(1.0, 1.0 - dist / (threshold * 2.0)))
    verified = dist < threshold

    logger.debug(
        "Face comparison | cosine_dist=%.4f threshold=%.3f verified=%s",
        dist, threshold, verified,
    )

    return {
        "verified":   verified,
        "confidence": round(confidence, 4),
        "distance":   round(dist, 4),
        "reason":     "match" if verified else "no_match",
    }
