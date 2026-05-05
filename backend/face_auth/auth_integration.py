"""
auth_integration.py — Bridge between face_service.py and the Django ORM.

Provides high-level operations consumed by the API views:

  enroll_face(user, b64_image)       -> EnrollResult dict
  verify_face_for_login(user, b64)   -> VerifyResult dict
  complete_face_login(user, request) -> issues DRF token + clears session

This module is the ONLY place that knows about UserFaceProfile, Token,
and session management; face_service.py stays ORM-free and testable.
"""

import logging

from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token

from .crypto import decrypt_embedding, encrypt_embedding
from .face_service import detect_and_validate, verify_faces
from .models import UserFaceProfile

logger = logging.getLogger(__name__)

_SESSION_PENDING_USER = "pending_2fa_user_id"
_MAX_FAILED_ATTEMPTS  = 5


# ── Enrollment ────────────────────────────────────────────────────────────────

def enroll_face(user: User, b64_image: str) -> dict:
    """
    Detect face, extract embedding, encrypt and persist it.

    Returns:
      {"ok": True,  "created": bool, "message": str}
      {"ok": False, "reason": str,   "detail":  str}
    """
    # Step 1 — detect + extract embedding via DeepFace
    result = detect_and_validate(b64_image)
    if not result["ok"]:
        return {"ok": False, "reason": result["reason"], "detail": result["detail"]}

    # Step 2 — encrypt embedding (never stored in plaintext)
    try:
        enc = encrypt_embedding(result["embedding"])
    except Exception as exc:  # noqa: BLE001
        logger.error("Embedding encryption failed for user_id=%s: %s", user.pk, exc, exc_info=True)
        return {
            "ok":     False,
            "reason": "system_error",
            "detail": "Could not secure face data. Please try again.",
        }

    # Step 3 — persist (upsert)
    try:
        _, created = UserFaceProfile.objects.update_or_create(
            user     = user,
            defaults = {"embedding_enc": enc, "is_active": True, "failed_attempts": 0},
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("DB write failed for user_id=%s: %s", user.pk, exc, exc_info=True)
        return {
            "ok":     False,
            "reason": "system_error",
            "detail": "Could not save face data. Please try again.",
        }

    action = "enrolled" if created else "re-enrolled"
    logger.info("Face %s | user_id=%s", action, user.pk)

    # Step 4 — enable face 2FA on the user's notification profile
    _activate_face_2fa(user)

    return {"ok": True, "created": created, "message": f"Face {action} successfully."}


# ── Verification ──────────────────────────────────────────────────────────────

def verify_face(user: User, b64_image: str) -> dict:
    """
    Verify a live selfie against the stored enrollment for *user*.

    Returns the standard VerifyResult dict:
      {
        "verified":          bool,
        "confidence":        float,
        "distance":          float,
        "reason":            str,
        "detail":            str,
        "fallback_available": bool,   # True when OTP fallback is possible
      }
    """
    # ── Pre-checks ────────────────────────────────────────────────────────────
    profile: UserFaceProfile | None = getattr(user, "face_profile", None)

    if not profile or not profile.is_active:
        return {
            "verified":          False,
            "confidence":        0.0,
            "distance":          1.0,
            "reason":            "no_enrollment",
            "detail":            "No face enrollment found for this account.",
            "fallback_available": True,
        }

    if profile.failed_attempts >= _MAX_FAILED_ATTEMPTS:
        logger.warning("Face auth locked | user_id=%s", user.pk)
        return {
            "verified":          False,
            "confidence":        0.0,
            "distance":          1.0,
            "reason":            "locked",
            "detail":            "Too many failed attempts. Face auth is locked. Use OTP to sign in.",
            "fallback_available": True,
        }

    # ── Decrypt stored embedding ──────────────────────────────────────────────
    try:
        stored_emb = decrypt_embedding(profile.embedding_enc)
    except Exception as exc:  # noqa: BLE001
        logger.error("Embedding decrypt failed for user_id=%s: %s", user.pk, exc)
        return {
            "verified":          False,
            "confidence":        0.0,
            "distance":          1.0,
            "reason":            "system_error",
            "detail":            "Enrollment data is corrupted. Please re-enroll your face.",
            "fallback_available": True,
        }

    # ── Compare via face_service ──────────────────────────────────────────────
    result = verify_faces(stored_emb, b64_image)

    # ── Update failure counter ────────────────────────────────────────────────
    if result["verified"]:
        profile.failed_attempts = 0
        profile.save(update_fields=["failed_attempts"])
        logger.info(
            "Face verification success | user_id=%s confidence=%.4f",
            user.pk, result["confidence"],
        )
    else:
        profile.failed_attempts += 1
        profile.save(update_fields=["failed_attempts"])
        remaining = max(0, _MAX_FAILED_ATTEMPTS - profile.failed_attempts)
        logger.warning(
            "Face verification failed | user_id=%s dist=%.4f remaining=%d",
            user.pk, result["distance"], remaining,
        )
        result["attempts_remaining"] = remaining
        result["fallback_available"] = True

    return result


def complete_face_login(user: User, request) -> dict:
    """
    Called after a successful face verification that was initiated as part of
    the 2FA login flow (session contains pending_2fa_user_id).

    Clears the pending session entry and returns a DRF auth token.

    Returns:
        {"token": str, "user": {"id", "username", "email"}}
    """
    # Clear the pending 2FA marker
    request.session.pop(_SESSION_PENDING_USER, None)
    request.session.save()

    token, _ = Token.objects.get_or_create(user=user)
    logger.info("Face 2FA login complete | user_id=%s", user.pk)
    return {
        "token": token.key,
        "user":  {"id": user.pk, "username": user.username, "email": user.email},
    }


# ── Internal helper ───────────────────────────────────────────────────────────

def _activate_face_2fa(user: User) -> None:
    """Set the 2FA method to 'face' after successful enrollment."""
    try:
        from notifications.models import UserTwoFAProfile  # noqa: PLC0415

        profile, _ = UserTwoFAProfile.objects.get_or_create(user=user)
        profile.twofa_enabled    = True
        profile.preferred_method = UserTwoFAProfile.METHOD_FACE
        profile.save(update_fields=["twofa_enabled", "preferred_method"])
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not update 2FA profile after enrollment: %s", exc)
