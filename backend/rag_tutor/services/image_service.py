"""
Local image extraction for multimodal RAG.

Images become text-grounded evidence through:
1. EasyOCR text extraction.
2. Optional Ollama vision captioning when a local vision model is installed.
"""

import base64
import logging
import os
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "moondream")


def _ordered_text(detections: List[Dict]) -> str:
    ordered = sorted(detections, key=lambda r: (r.get("y_min", 0), r.get("x_min", 0)))
    return "\n".join(str(r.get("text", "")).strip() for r in ordered if r.get("text"))


def _avg_confidence(detections: List[Dict]) -> float:
    if not detections:
        return 0.0
    return round(sum(float(r.get("confidence", 0.0)) for r in detections) / len(detections), 3)


def extract_ocr_text(image_bytes: bytes) -> Dict:
    """
    Run generic OCR on an uploaded image.

    Returns:
        {"text": str, "confidence": float, "detections": int}
    """
    try:
        from ocr.ocr_engine import run_ocr
        from ocr.preprocessor import _bytes_to_cv, _downscale_if_large, preprocess
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Image OCR dependencies are not available.") from exc

    detections: List[Dict] = []

    try:
        processed = preprocess(image_bytes)
        detections = run_ocr(processed, languages=["en", "fr"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Preprocessed OCR failed: %s", exc)

    try:
        raw_img = _downscale_if_large(_bytes_to_cv(image_bytes))
        raw_detections = run_ocr(raw_img, languages=["en", "fr"])
        if len(raw_detections) > len(detections):
            detections = raw_detections
    except Exception as exc:  # noqa: BLE001
        logger.debug("Raw OCR fallback skipped: %s", exc)

    return {
        "text": _ordered_text(detections),
        "confidence": _avg_confidence(detections),
        "detections": len(detections),
    }


def _ollama_model_installed(model_name: str) -> bool:
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=1.0)
        response.raise_for_status()
        names = {m.get("name", "") for m in response.json().get("models", [])}
        return (
            model_name in names
            or f"{model_name}:latest" in names
            or any(name.split(":", 1)[0] == model_name for name in names)
        )
    except Exception:
        return False


def describe_image_with_ollama(image_bytes: bytes) -> Dict:
    """
    Use a local Ollama vision model to produce a searchable description.
    If the configured model is not installed, returns an empty description.
    """
    if not _ollama_model_installed(OLLAMA_VISION_MODEL):
        return {
            "text": "",
            "provider": "none",
            "model": OLLAMA_VISION_MODEL,
            "available": False,
        }

    prompt = (
        "Describe this image for retrieval in a trading education RAG system. "
        "Capture visible text, chart patterns, indicators, axes, labels, diagrams, "
        "and any educational trading concepts. Do not give financial advice."
    )

    try:
        encoded = base64.b64encode(image_bytes).decode("ascii")
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_VISION_MODEL,
                "prompt": prompt,
                "images": [encoded],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 512},
            },
            timeout=90,
        )
        response.raise_for_status()
        data = response.json()
        return {
            "text": str(data.get("response", "")).strip(),
            "provider": "ollama",
            "model": OLLAMA_VISION_MODEL,
            "available": True,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Ollama vision extraction failed: %s", exc)
        return {
            "text": "",
            "provider": "ollama",
            "model": OLLAMA_VISION_MODEL,
            "available": True,
            "error": str(exc),
        }


def extract_image_evidence(filename: str, image_bytes: bytes) -> Dict:
    """
    Return a text representation and metadata for an image upload.
    """
    ocr = extract_ocr_text(image_bytes)
    # For text-heavy screenshots/infographics, exact OCR is usually more
    # trustworthy than a free-form vision caption. Captions are useful when OCR
    # is sparse, but they can blur labels and numbers in risk matrices.
    has_strong_ocr = bool(ocr["text"]) and ocr["detections"] >= 6 and ocr["confidence"] >= 0.35
    vision = (
        {
            "text": "",
            "provider": "skipped",
            "model": OLLAMA_VISION_MODEL,
            "available": _ollama_model_installed(OLLAMA_VISION_MODEL),
            "reason": "strong_ocr",
        }
        if has_strong_ocr
        else describe_image_with_ollama(image_bytes)
    )

    parts = []
    if ocr["text"]:
        parts.append(
            "OCR TEXT (authoritative visible text; keep nearby labels and values together):\n"
            + ocr["text"]
        )
    if vision["text"]:
        parts.append("VISUAL DESCRIPTION (lower confidence than OCR text):\n" + vision["text"])

    text = "\n\n".join(parts).strip()
    metadata = {
        "filename": filename,
        "ocr": {
            "confidence": ocr["confidence"],
            "detections": ocr["detections"],
        },
        "vision": {
            "provider": vision.get("provider", "none"),
            "model": vision.get("model", OLLAMA_VISION_MODEL),
            "available": bool(vision.get("available", False)),
            "reason": vision.get("reason", ""),
        },
    }
    if vision.get("error"):
        metadata["vision"]["error"] = vision["error"]

    return {"text": text, "metadata": metadata}
