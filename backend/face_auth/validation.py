"""
validation.py — Input validation helpers for face authentication endpoints.

All functions return structured dicts so views stay thin and testable.
"""

import base64
import logging

logger = logging.getLogger(__name__)

# Supported image MIME types / magic bytes identifiers
_ALLOWED_TYPES = {"jpeg", "png", "webp"}

# Max base64 payload size: ~4 MB (raw image ~3 MB after decode)
_MAX_B64_BYTES = 4 * 1024 * 1024


def _detect_image_format(raw_bytes: bytes) -> str | None:
    """
    Detect image format from magic bytes without relying on imghdr
    (removed from Python 3.13 stdlib).

    Returns 'jpeg', 'png', 'webp', or None.
    """
    if raw_bytes[:2] == b"\xff\xd8":
        return "jpeg"
    if raw_bytes[:8] == b"\x89PNG\r\n\x1a\n":
        return "png"
    if raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP":
        return "webp"
    return None


def validate_image_input(value: object) -> dict:
    """
    Validate a base64 image string before any heavy processing.

    Returns:
        {"valid": True, "b64": str}                   — stripped, clean base64
        {"valid": False, "reason": str, "detail": str} — error

    Checks performed:
      1. Type is non-empty string
      2. Payload size within limit
      3. Decodable base64
      4. Magic-bytes are a supported image format (jpeg / png / webp)
    """
    if not isinstance(value, str) or not value.strip():
        return {
            "valid":  False,
            "reason": "invalid_image",
            "detail": "Image field must be a non-empty string.",
        }

    b64 = value.strip()
    # Strip data-URI prefix
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    if len(b64) > _MAX_B64_BYTES:
        return {
            "valid":  False,
            "reason": "invalid_image",
            "detail": f"Image payload too large (max {_MAX_B64_BYTES // 1024} KB).",
        }

    # ── Decode ────────────────────────────────────────────────────────────────
    try:
        raw_bytes = base64.b64decode(b64, validate=True)
    except Exception:
        return {
            "valid":  False,
            "reason": "invalid_image",
            "detail": "Image is not valid base64 data.",
        }

    # ── Format detection via magic bytes ─────────────────────────────────────
    fmt = _detect_image_format(raw_bytes)

    if fmt not in _ALLOWED_TYPES:
        detected = fmt or "unknown"
        return {
            "valid":  False,
            "reason": "invalid_image",
            "detail": (
                f"Unsupported image format '{detected}'. "
                "Please upload a JPEG, PNG, or WebP image."
            ),
        }

    return {"valid": True, "b64": b64}


def validate_enroll_request(data: dict) -> dict:
    """
    Validate the POST body for the enroll endpoint.

    Expected fields:
      - image (required): base64 selfie

    Returns {"valid": True, "image": str} or error dict.
    """
    payload = data if isinstance(data, dict) else {}
    image_check = validate_image_input(payload.get("image", ""))
    if not image_check["valid"]:
        return image_check
    return {"valid": True, "image": image_check["b64"]}


def validate_verify_request(data: dict) -> dict:
    """
    Validate the POST body for the verify endpoint.

    Expected fields:
      - image (required):          base64 live selfie
      - challenge_id (optional):   UUID string
      - liveness_frame (optional): base64 second frame

    Returns {"valid": True, "image": str, ...} or error dict.
    """
    payload = data if isinstance(data, dict) else {}
    image_check = validate_image_input(payload.get("image", ""))
    if not image_check["valid"]:
        return image_check

    result: dict = {"valid": True, "image": image_check["b64"]}

    # Optional liveness frame
    liveness_raw = payload.get("liveness_frame", "")
    if liveness_raw:
        lf_check = validate_image_input(liveness_raw)
        if not lf_check["valid"]:
            return {
                "valid":  False,
                "reason": "invalid_image",
                "detail": f"liveness_frame: {lf_check['detail']}",
            }
        result["liveness_frame"] = lf_check["b64"]
    else:
        result["liveness_frame"] = ""

    # Optional challenge_id — just pass through as string
    result["challenge_id"] = str(payload.get("challenge_id") or "").strip()

    return result
