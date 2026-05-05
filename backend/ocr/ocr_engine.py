"""
OCR engine module.

Wraps EasyOCR with lazy initialisation and module-level caching so the
heavy model weights are loaded only once per process.

Returns structured detections that include:
  - text        : recognised string
  - bbox        : [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]  (top-left clockwise)
  - confidence  : float 0-1
  - center      : (cx, cy)  geometric centre
  - x_min/max, y_min/max : bounding rect edges
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

# Supported language sets — order matters for detection priority
# EasyOCR constraint: Arabic (ar) can ONLY be paired with English, never with
# Latin-script languages like French. Use separate readers for each script family.
LANGUAGE_PRESETS: Dict[str, List[str]] = {
    "default": ["en", "fr"],              # Latin scripts (covers most EU/Maghreb cards)
    "latin":   ["en", "fr", "de", "es", "pt"],
    "arabic":  ["en", "ar"],              # Arabic only compatible with English
}

# Module-level cache: one reader instance per language combination
_reader_cache: Dict[str, Any] = {}


def get_reader(languages: Optional[List[str]] = None) -> Any:
    """
    Return a cached EasyOCR Reader for the given language list.

    First call per language set downloads model weights (~300 MB) and
    initialises the neural network, which can take 10-30 s.
    Subsequent calls are instant.

    Raises RuntimeError if EasyOCR is not installed.
    """
    if languages is None:
        languages = LANGUAGE_PRESETS["default"]

    cache_key = ",".join(sorted(languages))
    if cache_key not in _reader_cache:
        try:
            import easyocr  # noqa: PLC0415
        except ImportError:
            raise RuntimeError(
                "EasyOCR is not installed. "
                "Run:  pip install easyocr"
            )
        logger.info("Initialising EasyOCR reader (languages=%s) …", languages)
        _reader_cache[cache_key] = easyocr.Reader(languages, gpu=False)
        logger.info("EasyOCR reader ready.")

    return _reader_cache[cache_key]


def run_ocr(
    img: np.ndarray,
    languages: Optional[List[str]] = None,
    min_confidence: float = 0.2,
) -> List[Dict[str, Any]]:
    """
    Run OCR on a preprocessed image.

    Args:
        img            : Grayscale or colour numpy array.
        languages      : Language codes for EasyOCR (default: en/fr/ar).
        min_confidence : Discard detections below this confidence.

    Returns:
        List of dicts — one per detected text region.
    """
    reader = get_reader(languages)
    raw = reader.readtext(img)

    results: List[Dict[str, Any]] = []
    for bbox, text, confidence in raw:
        text = text.strip()
        if not text or confidence < min_confidence:
            continue

        # Skip single-character detections with < 60% confidence: almost always noise
        if len(text) == 1 and confidence < 0.60:
            continue

        xs = [p[0] for p in bbox]
        ys = [p[1] for p in bbox]
        results.append(
            {
                "text":       text,
                "bbox":       bbox,
                "confidence": float(confidence),
                "center":     (sum(xs) / len(xs), sum(ys) / len(ys)),
                "x_min":      float(min(xs)),
                "x_max":      float(max(xs)),
                "y_min":      float(min(ys)),
                "y_max":      float(max(ys)),
            }
        )

    logger.debug("OCR returned %d detections", len(results))
    return results
