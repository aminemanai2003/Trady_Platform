"""
Liveness detection — anti-spoofing layer.

Two complementary strategies are implemented:

  1. Single-frame texture check
       Laplacian variance on the face region.  An extremely blurry face is a
       possible photo-of-photo attack; we reject it early.

  2. Two-frame challenge-response  (primary anti-spoof mechanism)
       The client requests a challenge (GET /api/face-auth/liveness/challenge/),
       performs the requested action in front of the camera, and submits two
       frames — one *before* and one *during/after* the action.

     Challenge actions:
       "blink"  — detect eye-closure via Eye Aspect Ratio (EAR) change.
                  Falls back to frame-difference motion check when landmarks
                  are not available (e.g. facenet-pytorch backend with 5-pt lm).
       "motion" — verify that a minimum fraction of pixels changed between the
                  two frames, proving the capture is a live video stream.

NOTE: This is a defence-in-depth layer, not a certified ISO/IEC 30107 PAD system.
      For production deployments processing high-risk transactions, swap the
      two-frame check with a dedicated neural liveness model.
"""

import logging
import random
import uuid
from datetime import timedelta

import cv2
import numpy as np
from django.utils import timezone

logger = logging.getLogger(__name__)

# ── Configuration ─────────────────────────────────────────────────────────────
_ACTIONS               = ["blink", "motion"]
_CHALLENGE_EXPIRY_MIN  = 2
_MOTION_THRESHOLD      = 0.015   # fraction of pixels that must differ
_EAR_DIFF_MIN          = 0.08    # minimum EAR change to count as a blink
_EAR_CLOSED_MAX        = 0.22    # EAR below this is considered "eye closed"
_LAP_MIN               = 20.0    # minimum Laplacian variance (single-frame check)


# ── Eye Aspect Ratio helpers ──────────────────────────────────────────────────

def _eye_aspect_ratio(eye_points: list) -> float:
    """
    Compute EAR from a list of (x, y) eye landmark points.

    For 6-point eyes (face_recognition):
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
    For 1-point eyes (MTCNN centre only): returns a neutral 0.25.
    """
    pts = np.array(eye_points, dtype=np.float64)
    if len(pts) < 6:
        return 0.25  # single-point landmark — assume open
    A = np.linalg.norm(pts[1] - pts[5])
    B = np.linalg.norm(pts[2] - pts[4])
    C = np.linalg.norm(pts[0] - pts[3])
    if C == 0.0:
        return 0.0
    return float((A + B) / (2.0 * C))


def _mean_ear(landmarks: dict) -> float:
    """Average EAR across both eyes from a landmarks dict."""
    left  = landmarks.get("left_eye",  [])
    right = landmarks.get("right_eye", [])
    if not left or not right:
        return 0.25
    return (_eye_aspect_ratio(left) + _eye_aspect_ratio(right)) / 2.0


# ── Single-frame check ────────────────────────────────────────────────────────

def check_single_frame_liveness(img_rgb: np.ndarray, face_loc) -> dict:
    """
    Basic single-frame anti-spoof heuristic: reject clearly blurry frames
    that may indicate a printed / screen-replayed photo.

    Returns:
        {"passed": bool, "reason": str | None, "detail": str}
    """
    top, right, bottom, left = face_loc
    face_crop = img_rgb[top:bottom, left:right]
    gray = cv2.cvtColor(face_crop, cv2.COLOR_RGB2GRAY)
    lap_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())

    if lap_var < _LAP_MIN:
        return {
            "passed": False,
            "reason": "spoof_detected",
            "detail": f"Face image is excessively blurry (Laplacian={lap_var:.1f}). Possible photo attack.",
        }
    return {"passed": True, "reason": None, "detail": "Single-frame check passed."}


# ── Two-frame challenge system ────────────────────────────────────────────────

def generate_challenge(session_key: str = "") -> dict:
    """
    Create a new liveness challenge record and return the details to send
    to the frontend.

    The challenge_id is a UUID that the client must include when submitting
    the two verification frames.

    Returns:
        {
            "challenge_id": "<uuid>",
            "action":       "blink" | "motion",
            "instruction":  "<human-readable prompt>",
            "expires_at":   "<ISO 8601 datetime>",
        }
    """
    from .models import FaceLivenessChallenge

    action = random.choice(_ACTIONS)  # noqa: S311 — not security-sensitive
    instructions = {
        "blink":  "Please blink once naturally in front of the camera.",
        "motion": "Please slowly turn your head slightly to the left or right.",
    }

    challenge = FaceLivenessChallenge.objects.create(
        challenge_id=uuid.uuid4(),
        action=action,
        session_key=session_key,
        expires_at=timezone.now() + timedelta(minutes=_CHALLENGE_EXPIRY_MIN),
    )
    return {
        "challenge_id": str(challenge.challenge_id),
        "action":       action,
        "instruction":  instructions[action],
        "expires_at":   challenge.expires_at.isoformat(),
    }


def validate_challenge(
    challenge_id: str,
    frame1_rgb: np.ndarray,
    frame2_rgb: np.ndarray,
    session_key: str = "",
) -> dict:
    """
    Validate a submitted liveness challenge using two captured frames.

    frame1 — captured BEFORE the requested action (baseline)
    frame2 — captured DURING / AFTER the action

    Returns:
        {"passed": bool, "reason": "match" | "spoof_detected", "detail": str}
    """
    from .models import FaceLivenessChallenge

    try:
        challenge = FaceLivenessChallenge.objects.get(challenge_id=challenge_id)
    except FaceLivenessChallenge.DoesNotExist:
        return {"passed": False, "reason": "spoof_detected", "detail": "Challenge token not found."}

    if challenge.is_used:
        return {"passed": False, "reason": "spoof_detected", "detail": "Challenge already consumed."}

    if challenge.expires_at < timezone.now():
        return {"passed": False, "reason": "spoof_detected", "detail": "Challenge expired. Request a new one."}

    if session_key and challenge.session_key and challenge.session_key != session_key:
        logger.warning("Liveness session mismatch | challenge_id=%s", challenge_id)
        return {"passed": False, "reason": "spoof_detected", "detail": "Session mismatch."}

    # Consume the token immediately to prevent replay
    challenge.is_used = True
    challenge.save(update_fields=["is_used"])

    if challenge.action == "blink":
        return _check_blink(frame1_rgb, frame2_rgb)
    return _check_motion(frame1_rgb, frame2_rgb)


# ── Inner validators ──────────────────────────────────────────────────────────

def _check_blink(frame1_rgb: np.ndarray, frame2_rgb: np.ndarray) -> dict:
    """
    Detect a blink by comparing Eye Aspect Ratio between two frames.
    Falls back to motion check when landmarks are unavailable.
    """
    from .embedding_extraction import get_landmarks

    lm1 = get_landmarks(frame1_rgb)
    lm2 = get_landmarks(frame2_rgb)

    if lm1 is None or lm2 is None:
        logger.debug("No landmarks available for blink check — falling back to motion.")
        return _check_motion(frame1_rgb, frame2_rgb)

    ear1 = _mean_ear(lm1)
    ear2 = _mean_ear(lm2)
    ear_diff = abs(ear1 - ear2)
    ear_min  = min(ear1, ear2)

    logger.debug("Blink check | EAR1=%.3f EAR2=%.3f diff=%.3f min=%.3f", ear1, ear2, ear_diff, ear_min)

    # Significant EAR drop AND at least one frame shows closed eyes
    if ear_diff >= _EAR_DIFF_MIN and ear_min < _EAR_CLOSED_MAX:
        return {"passed": True, "reason": "match", "detail": "Blink detected."}

    # Generous fallback: accept if frames differ enough overall
    motion_result = _check_motion(frame1_rgb, frame2_rgb)
    if motion_result["passed"]:
        return motion_result

    return {
        "passed": False,
        "reason": "spoof_detected",
        "detail": "No blink detected. Please blink naturally in front of the camera.",
    }


def _check_motion(frame1_rgb: np.ndarray, frame2_rgb: np.ndarray) -> dict:
    """
    Verify live presence by measuring pixel-level change between two frames.

    A static image replay (photo / looped video) produces near-zero difference.
    """
    g1 = cv2.cvtColor(frame1_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)
    g2 = cv2.cvtColor(frame2_rgb, cv2.COLOR_RGB2GRAY).astype(np.float32)

    if g1.shape != g2.shape:
        # Resize to the same dimensions if the client sent mismatched sizes
        g2 = cv2.resize(g2, (g1.shape[1], g1.shape[0]), interpolation=cv2.INTER_AREA)

    diff = np.abs(g1 - g2)
    changed_frac = float((diff > 10).sum()) / diff.size

    logger.debug("Motion check | changed=%.4f threshold=%.4f", changed_frac, _MOTION_THRESHOLD)

    if changed_frac > _MOTION_THRESHOLD:
        return {
            "passed": True,
            "reason": "match",
            "detail": f"Motion detected ({changed_frac:.1%} pixels changed).",
        }
    return {
        "passed": False,
        "reason": "spoof_detected",
        "detail": (
            "No movement detected between frames. "
            "Possible photo or screen replay attack."
        ),
    }
