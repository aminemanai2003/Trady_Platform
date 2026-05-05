"""
Face detection and image quality assessment.

Supported backends (auto-detected at runtime):
  1. face_recognition (dlib)     — preferred; better landmark support.
  2. facenet-pytorch  (MTCNN)    — easier pip install on Windows; uses PyTorch.

Install one of:
  Option A (recommended on Windows):
      pip install facenet-pytorch          # already needs torch (in requirements)
  Option B (preferred by spec, harder on Windows):
      pip install cmake dlib face_recognition
"""

import base64
import logging
from typing import NamedTuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)

# ── Quality thresholds (can be overridden via env vars) ───────────────────────
_MIN_FACE_PX   = 80     # minimum face side (height or width) in pixels
_MIN_BRIGHTNESS = 40    # face-region mean intensity (0–255)
_MAX_BRIGHTNESS = 238
_MIN_SHARPNESS  = 40.0  # Laplacian variance in the cropped face region


class FaceLocation(NamedTuple):
    top: int
    right: int
    bottom: int
    left: int


# ── Image decoding ────────────────────────────────────────────────────────────

def decode_b64_image(b64_str: str) -> np.ndarray:
    """
    Decode a base64-encoded image (optionally with data-URI prefix) to a
    numpy uint8 RGB array.

    Raises:
        ValueError: If the data is not valid base64 or cannot be decoded as
                    a supported image format.
    """
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    try:
        img_bytes = base64.b64decode(b64_str.strip())
    except Exception as exc:
        raise ValueError(f"Invalid base64 data: {exc}") from exc

    nparr = np.frombuffer(img_bytes, np.uint8)
    bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if bgr is None:
        raise ValueError(
            "Could not decode image (unsupported format or corrupted data)."
        )
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


# ── Face detection ────────────────────────────────────────────────────────────

def detect_faces(img_rgb: np.ndarray) -> list:
    """
    Detect all faces in an RGB numpy image.

    Returns:
        list of FaceLocation(top, right, bottom, left) named tuples.

    Raises:
        RuntimeError: If no face detection backend is available.
    """
    # ── Backend 1: face_recognition (dlib) ───────────────────────────────────
    try:
        import face_recognition

        raw = face_recognition.face_locations(
            img_rgb, model="hog", number_of_times_to_upsample=1
        )
        return [FaceLocation(top=t, right=r, bottom=b, left=l) for t, r, b, l in raw]
    except ImportError:
        pass

    # ── Backend 2: facenet-pytorch MTCNN ─────────────────────────────────────
    try:
        from PIL import Image
        from facenet_pytorch import MTCNN

        mtcnn = MTCNN(keep_all=True, device="cpu", margin=20, min_face_size=60, post_process=False)
        pil = Image.fromarray(img_rgb)
        boxes, _ = mtcnn.detect(pil)
        if boxes is None:
            return []
        results = []
        for box in boxes:
            x1, y1, x2, y2 = (max(0, int(v)) for v in box)
            results.append(FaceLocation(top=y1, right=x2, bottom=y2, left=x1))
        return results
    except ImportError:
        pass

    raise RuntimeError(
        "No face detection backend available. Install one:\n"
        "  Option A (easier on Windows): pip install facenet-pytorch\n"
        "  Option B: pip install cmake dlib face_recognition"
    )


# ── Quality assessment ────────────────────────────────────────────────────────

def check_quality(img_rgb: np.ndarray, face_loc: FaceLocation) -> dict:
    """
    Assess whether a face image meets quality requirements for enrollment
    and verification.

    Returns:
        {
            "passed":  bool,
            "reason":  "low_quality" | None,
            "detail":  str — human-readable explanation,
            "metrics": dict — raw measurements for debugging,
        }
    """
    top, right, bottom, left = face_loc
    face_h = bottom - top
    face_w = right - left
    img_h, img_w = img_rgb.shape[:2]
    metrics: dict = {}

    # 1. Face size ─────────────────────────────────────────────────────────────
    if face_h < _MIN_FACE_PX or face_w < _MIN_FACE_PX:
        return {
            "passed": False,
            "reason": "low_quality",
            "detail": f"Face too small ({face_w}×{face_h}px). Move closer to the camera.",
            "metrics": metrics,
        }

    # 2. Centering — face centre must be in the middle 70% of the frame ────────
    cx = (left + right) / 2 / img_w
    cy = (top + bottom) / 2 / img_h
    metrics["face_center_x"] = round(cx, 3)
    metrics["face_center_y"] = round(cy, 3)
    if not (0.15 <= cx <= 0.85 and 0.10 <= cy <= 0.90):
        return {
            "passed": False,
            "reason": "low_quality",
            "detail": "Face is off-center. Position yourself in the middle of the frame.",
            "metrics": metrics,
        }

    # 3. Brightness ────────────────────────────────────────────────────────────
    face_crop = img_rgb[top:bottom, left:right]
    gray = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY)
    brightness = float(gray.mean())
    metrics["brightness"] = round(brightness, 1)
    if brightness < _MIN_BRIGHTNESS:
        return {
            "passed": False,
            "reason": "low_quality",
            "detail": "Image too dark. Please improve lighting.",
            "metrics": metrics,
        }
    if brightness > _MAX_BRIGHTNESS:
        return {
            "passed": False,
            "reason": "low_quality",
            "detail": "Image overexposed. Reduce direct light or move away from the source.",
            "metrics": metrics,
        }

    # 4. Sharpness (Laplacian variance) ────────────────────────────────────────
    sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    metrics["sharpness"] = round(sharpness, 1)
    if sharpness < _MIN_SHARPNESS:
        return {
            "passed": False,
            "reason": "low_quality",
            "detail": "Image is blurry. Hold the camera steady and ensure good focus.",
            "metrics": metrics,
        }

    return {
        "passed": True,
        "reason": None,
        "detail": "Quality check passed.",
        "metrics": metrics,
    }
