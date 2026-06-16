"""
face_service.py — Core face recognition logic using DeepFace.

Public API
----------
detect_and_validate(b64_or_array) -> FaceResult
    Decode, quality-check, detect exactly one face, extract embedding.

verify_faces(stored_embedding, live_b64) -> VerifyResult
    Compare a stored embedding vector against a fresh base64 image.

All functions return structured result dicts — they NEVER raise exceptions
to the caller. Errors are expressed as result["ok"] == False + result["reason"].
"""

import base64
import logging
import os
import threading
from typing import Any

import cv2
import numpy as np

try:
    from deepface import DeepFace as _DeepFace
except Exception:  # noqa: BLE001
    _DeepFace = None

logger = logging.getLogger(__name__)

DeepFace = _DeepFace

# ── DeepFace configuration ────────────────────────────────────────────────────
# ArcFace (ResNet50-based, 512-d) offers best accuracy on standard benchmarks.
# opencv detector is the most permissive — works well with standard webcams.
# Change DEEPFACE_DETECTOR env var to "retinaface" for stricter production use.
_MODEL_NAME    = os.getenv("DEEPFACE_MODEL",    "ArcFace")
_DETECTOR_NAME = os.getenv("DEEPFACE_DETECTOR", "opencv")
# Fallback detectors tried in order if the primary detector finds no face
_FALLBACK_DETECTORS = ["ssd", "mtcnn"]
_DISTANCE_METRIC = "cosine"

# Cosine distance threshold — embeddings closer than this are the same person.
# ArcFace cosine default is 0.40; lower = stricter.
_THRESHOLD = float(os.getenv("FACE_SIMILARITY_THRESHOLD", "0.40"))

# Minimum resolution gate (face bounding-box side, pixels) — relaxed for webcam
_MIN_FACE_PX = int(os.getenv("FACE_MIN_PX", "40"))

# Brightness gates (mean pixel intensity on face crop, 0-255) — relaxed
_MIN_BRIGHTNESS = int(os.getenv("FACE_MIN_BRIGHTNESS", "20"))
_MAX_BRIGHTNESS = int(os.getenv("FACE_MAX_BRIGHTNESS", "250"))

# Sharpness gate (Laplacian variance on face crop) — relaxed for webcam
_MIN_SHARPNESS = float(os.getenv("FACE_MIN_SHARPNESS", "0.0"))

# ── Lazy model warm-up ────────────────────────────────────────────────────────
_model_lock   = threading.Lock()
_model_warmed = False


def _warmup_deepface() -> None:
    """
    Force DeepFace to download and cache BOTH the recognition model (ArcFace)
    AND the face detector (retinaface) weights on startup, so that the first
    real API request is not penalised by a multi-minute model download.

    Uses enforce_detection=False on a blank image so detection failure is fine.
    """
    global _model_warmed
    with _model_lock:
        if _model_warmed:
            return
        try:
            deepface = _get_deepface()
            # A blank 100×100 image — detection will silently fail, but that's
            # OK: we only care about triggering the weight-download + file-cache.
            dummy = np.zeros((100, 100, 3), dtype=np.uint8)
            try:
                deepface.represent(
                    img_path          = dummy,
                    model_name        = _MODEL_NAME,
                    detector_backend  = "opencv",   # fastest detector for warmup
                    enforce_detection = False,
                    align             = False,
                )
            except Exception:  # noqa: BLE001
                pass  # expected on a blank image; weights are already cached
            logger.info(
                "DeepFace warmed up: model=%s detector=%s",
                _MODEL_NAME, _DETECTOR_NAME,
            )
            _model_warmed = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("DeepFace warm-up failed (will retry on first request): %s", exc)


def _get_deepface():
    global DeepFace

    if DeepFace is None:
        from deepface import DeepFace as deepface_class  # noqa: PLC0415
        DeepFace = deepface_class

    return DeepFace


# Fire warm-up in background thread — don't block Django startup
threading.Thread(target=_warmup_deepface, daemon=True).start()


# ── Image utilities ───────────────────────────────────────────────────────────

def decode_image(raw: "str | np.ndarray") -> np.ndarray:
    """
    Accept a base64 string (with or without data-URI prefix) OR an already-
    decoded numpy uint8 BGR array and always return a BGR uint8 ndarray.

    Raises:
        ValueError — unparseable input or corrupt image bytes.
    """
    if isinstance(raw, np.ndarray):
        if raw.dtype != np.uint8:
            raise ValueError("Image array must be uint8.")
        return raw  # already decoded

    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("Image must be a non-empty base64 string.")

    b64 = raw.strip()
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    try:
        img_bytes = base64.b64decode(b64)
    except Exception as exc:
        raise ValueError(f"Base64 decode error: {exc}") from exc

    arr = np.frombuffer(img_bytes, np.uint8)
    bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(
            "Could not decode image data (unsupported format or corrupted bytes)."
        )
    return bgr


def _crop_face(bgr: np.ndarray, region: dict) -> np.ndarray:
    """Crop the face region from a BGR image given a DeepFace region dict."""
    x, y, w, h = region["x"], region["y"], region["w"], region["h"]
    # Clamp to image bounds
    x, y = max(0, x), max(0, y)
    x2   = min(bgr.shape[1], x + w)
    y2   = min(bgr.shape[0], y + h)
    return bgr[y:y2, x:x2]


# ── Quality assessment (runs on the face crop) ────────────────────────────────

def _quality_check(face_crop: np.ndarray) -> dict:
    """
    Returns {"passed": True} or {"passed": False, "reason": ..., "detail": ...}.
    """
    h, w = face_crop.shape[:2]

    # ── Resolution ────────────────────────────────────────────────────────────
    if h < _MIN_FACE_PX or w < _MIN_FACE_PX:
        return {
            "passed": False,
            "reason": "low_quality",
            "detail": (
                f"Face is too small ({w}×{h} px). "
                f"Please move closer to the camera (min {_MIN_FACE_PX} px)."
            ),
        }

    # ── Brightness ────────────────────────────────────────────────────────────
    gray  = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
    mean  = float(np.mean(gray))
    if mean < _MIN_BRIGHTNESS:
        return {
            "passed": False,
            "reason": "low_quality",
            "detail": f"Image is too dark (brightness {mean:.0f}/255). Improve lighting.",
        }
    if mean > _MAX_BRIGHTNESS:
        return {
            "passed": False,
            "reason": "low_quality",
            "detail": f"Image is overexposed (brightness {mean:.0f}/255). Reduce lighting.",
        }

    # ── Sharpness (Laplacian variance) ────────────────────────────────────────
    if _MIN_SHARPNESS > 0:
        lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        if lap < _MIN_SHARPNESS:
            return {
                "passed": False,
                "reason": "low_quality",
                "detail": f"Image is blurry (sharpness {lap:.1f}, min {_MIN_SHARPNESS}). Hold still.",
            }

    return {"passed": True}


# ── Main detection + extraction pipeline ─────────────────────────────────────

def detect_and_validate(image_input: "str | np.ndarray") -> dict:
    """
    Full pipeline: decode → detect faces → quality check → extract embedding.

    Returns a result dict:

      On success:
        {
          "ok": True,
          "embedding": list[float],   # do NOT log or expose this
          "face_count": 1,
        }

      On failure:
        {
          "ok": False,
          "reason": "invalid_image" | "no_face" | "multiple_faces"
                    | "low_quality" | "system_error",
          "detail": str,
        }
    """
    deepface = _get_deepface()

    # ── 1. Decode ─────────────────────────────────────────────────────────────
    try:
        bgr = decode_image(image_input)
    except ValueError as exc:
        return {"ok": False, "reason": "invalid_image", "detail": str(exc)}

    # ── 2. Detect faces — try primary detector then fallbacks ─────────────────
    faces = None
    used_detector = _DETECTOR_NAME
    had_backend_error = False
    for detector in [_DETECTOR_NAME] + _FALLBACK_DETECTORS:
        try:
            faces = deepface.extract_faces(
                img_path          = bgr,
                detector_backend  = detector,
                enforce_detection = True,
                align             = True,
            )
            used_detector = detector
            break  # success — stop trying
        except ValueError:
            # No face found with this detector — try next
            faces = []
            continue
        except Exception as exc:  # noqa: BLE001
            logger.error("DeepFace extract_faces error (%s): %s", detector, exc, exc_info=True)
            had_backend_error = True
            faces = []
            continue

    if faces is None or len(faces) == 0:
        if had_backend_error:
            return {
                "ok": False,
                "reason": "system_error",
                "detail": "Face detection failed internally. Please try again.",
            }
        return {
            "ok": False,
            "reason": "no_face",
            "detail": "No face detected. Please look directly at the camera and ensure good lighting.",
        }

    # ── 3. Cardinality check ──────────────────────────────────────────────────
    if len(faces) > 1:
        return {
            "ok": False,
            "reason": "multiple_faces",
            "detail": f"{len(faces)} faces detected. Only you should be in the frame.",
        }

    face_obj = faces[0]
    region   = face_obj.get("facial_area", {})

    # ── 4. Quality check ──────────────────────────────────────────────────────
    if region:
        crop   = _crop_face(bgr, region)
        qcheck = _quality_check(crop)
        if not qcheck["passed"]:
            return {"ok": False, "reason": qcheck["reason"], "detail": qcheck["detail"]}

    # ── 5. Extract embedding ──────────────────────────────────────────────────
    try:
        # represent() returns a list of dicts, one per detected face.
        repr_list = deepface.represent(
            img_path          = bgr,
            model_name        = _MODEL_NAME,
            detector_backend  = used_detector,
            enforce_detection = True,
            align             = True,
        )
    except ValueError as exc:
        return {
            "ok": False,
            "reason": "no_face",
            "detail": "Could not extract face features. Make sure your face is visible.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("DeepFace represent error: %s", exc, exc_info=True)
        return {
            "ok": False,
            "reason": "system_error",
            "detail": "Embedding extraction failed. Please try again.",
        }

    # Guard against empty lists or unexpected shapes
    if not repr_list or "embedding" not in repr_list[0]:
        return {
            "ok": False,
            "reason": "system_error",
            "detail": "Embedding extraction returned an empty result.",
        }

    embedding: list[float] = repr_list[0]["embedding"]

    return {
        "ok":         True,
        "embedding":  embedding,
        "face_count": len(repr_list),
    }


# ── Verification ──────────────────────────────────────────────────────────────

def verify_faces(stored_embedding: list[float], live_image_input: "str | np.ndarray") -> dict:
    """
    Compare a stored enrollment embedding against a fresh image.

    Returns:
      {
        "verified":   bool,
        "confidence": float,   # 0.0 (no match) → 1.0 (perfect match)
        "distance":   float,
        "reason":     "match" | "no_face" | "multiple_faces" | "low_quality"
                      | "invalid_image" | "system_error",
        "detail":     str,
      }
    """
    # ── Detect + extract live embedding ──────────────────────────────────────
    if isinstance(live_image_input, list) or (
        isinstance(live_image_input, np.ndarray) and live_image_input.ndim == 1
    ):
        live_embedding = list(np.asarray(live_image_input, dtype=np.float64))
    else:
        live_result = detect_and_validate(live_image_input)
        if not live_result["ok"]:
            return {
                "verified":   False,
                "confidence": 0.0,
                "distance":   1.0,
                "reason":     live_result["reason"],
                "detail":     live_result["detail"],
            }

        live_embedding = live_result["embedding"]

    # ── Compare using DeepFace built-in distance metric  ────────────────────
    try:
        distance = _cosine_distance(stored_embedding, live_embedding)
    except Exception as exc:  # noqa: BLE001
        logger.error("Distance computation error: %s", exc, exc_info=True)
        return {
            "verified":   False,
            "confidence": 0.0,
            "distance":   1.0,
            "reason":     "system_error",
            "detail":     "Face comparison failed internally.",
        }

    verified   = distance < _THRESHOLD
    # Map distance [0, threshold*2] → confidence [1, 0] — clamp to [0,1]
    confidence = float(max(0.0, min(1.0, 1.0 - distance / (_THRESHOLD * 2))))

    return {
        "verified":   verified,
        "confidence": round(confidence, 4),
        "distance":   round(distance,   4),
        "reason":     "match" if verified else "no_match",
        "detail":     "Face matched." if verified else "Face did not match enrolled profile.",
    }


# ── Cosine distance helper ────────────────────────────────────────────────────

def _cosine_distance(a: "list | np.ndarray", b: "list | np.ndarray") -> float:
    """Cosine distance in [0, 2]. 0 = identical."""
    a = np.array(a, dtype=np.float64)
    b = np.array(b, dtype=np.float64)
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0.0 or nb == 0.0:
        return 2.0
    return float(1.0 - np.dot(a, b) / (na * nb))
