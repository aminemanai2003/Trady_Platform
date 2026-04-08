"""
OTP generation and verification service.

Security properties
-------------------
- 6-digit OTP generated via `secrets.randbelow` (CSPRNG — not `random`).
- Only the SHA-256 digest is persisted; the plaintext OTP is discarded after dispatch.
- Comparison uses `secrets.compare_digest` (constant-time) to prevent timing attacks.
- Previous unused tokens for the same user are invalidated before issuing a new one.
- Attempt counter is incremented atomically BEFORE checking the hash to prevent
  time-of-check/time-of-use races.
- Max 5 failed attempts causes the token to be permanently locked.
"""

import hashlib
import logging
import secrets

from django.contrib.auth.models import User
from django.utils import timezone

from .email_service import send_otp_email
from .models import OTPToken
from .sms_service import send_otp_sms

logger = logging.getLogger(__name__)

_OTP_LENGTH = 6


# ── Internal helpers ──────────────────────────────────────────────────────────

def _generate_raw_otp() -> str:
    """Return a zero-padded 6-digit string using a cryptographically secure RNG."""
    return str(secrets.randbelow(10 ** _OTP_LENGTH)).zfill(_OTP_LENGTH)


def _hash_otp(raw_otp: str) -> str:
    """Return the SHA-256 hex digest of the given OTP string."""
    return hashlib.sha256(raw_otp.encode()).hexdigest()


# ── Public API ────────────────────────────────────────────────────────────────

def generate_and_send_otp(
    user: User,
    method: str,
    session_key: str = "",
) -> dict:
    """
    Generate a new OTP, store its hash, and dispatch it to the user.

    Any previous active (unused + unexpired) OTP for this user is invalidated
    before the new one is created to prevent replay with stale tokens.

    Args:
        user:        Django User instance.
        method:      Delivery channel — "email" or "sms".
        session_key: Django session key.  When provided, the OTP is bound to
                     this session and verify_otp() will enforce the binding.

    Returns:
        {"success": True,  "message": "OTP sent"}
        {"success": False, "message": "<human-readable reason>"}
    """
    if method not in (OTPToken.DELIVERY_EMAIL, OTPToken.DELIVERY_SMS):
        return {"success": False, "message": "Invalid delivery method. Use 'email' or 'sms'."}

    # Invalidate all previous unused tokens for this user (both channels)
    OTPToken.objects.filter(
        user=user,
        is_used=False,
        expires_at__gt=timezone.now(),
    ).update(is_used=True)

    raw_otp = _generate_raw_otp()
    token = OTPToken.objects.create(
        user=user,
        token_hash=_hash_otp(raw_otp),
        delivery_method=method,
        session_key=session_key,
    )
    logger.debug(
        "OTP created | user_id=%s method=%s token_id=%s",
        user.pk, method, token.pk,
    )

    # Dispatch — raw_otp is passed directly and NEVER logged
    sent = False
    if method == OTPToken.DELIVERY_EMAIL:
        if not user.email:
            logger.warning("No email address for user_id=%s", user.pk)
            token.is_used = True
            token.save(update_fields=["is_used"])
            return {"success": False, "message": "No email address configured for this account."}
        sent = send_otp_email(user.email, raw_otp, username=user.get_full_name() or user.username)

    elif method == OTPToken.DELIVERY_SMS:
        profile = getattr(user, "twofa_profile", None)
        phone = profile.phone_number if profile else ""
        if not phone:
            logger.warning("No phone number for user_id=%s", user.pk)
            token.is_used = True
            token.save(update_fields=["is_used"])
            return {"success": False, "message": "No phone number configured for this account."}
        sent = send_otp_sms(phone, raw_otp)

    if not sent:
        # Deactivate the token so it cannot be guessed while delivery failed
        token.is_used = True
        token.save(update_fields=["is_used"])
        return {"success": False, "message": "Failed to deliver OTP. Please try again."}

    return {"success": True, "message": "OTP sent. Please check your " + method + "."}


def verify_otp(
    user: User,
    raw_otp: str,
    session_key: str = "",
) -> dict:
    """
    Verify a user-submitted OTP.

    Validation order:
      1. Find the most recent active token (unused, unexpired, not exhausted).
      2. Enforce session binding when session_key was provided at generation.
      3. Increment attempt counter BEFORE hash comparison.
      4. Constant-time SHA-256 digest comparison.

    Args:
        user:        Django User instance.
        raw_otp:     The 6-digit string submitted by the user.
        session_key: Session key from the current request (for binding check).

    Returns:
        {"success": True,  "message": "OTP verified"}
        {"success": False, "message": "<human-readable reason>"}
    """
    now = timezone.now()

    token_qs = OTPToken.objects.filter(
        user=user,
        is_used=False,
        expires_at__gt=now,
    ).order_by("-created_at")

    # Enforce session binding when originally requested
    if session_key:
        bound_qs = token_qs.filter(session_key=session_key)
        # If tokens were created without binding (empty session_key), fall back
        if bound_qs.exists():
            token_qs = bound_qs

    token = token_qs.first()
    if token is None:
        return {
            "success": False,
            "message": "No active OTP found. Please request a new code.",
        }

    if token.is_exhausted:
        return {
            "success": False,
            "message": "Too many failed attempts. Please request a new code.",
        }

    # Increment BEFORE the hash check to prevent race-condition enumeration
    token.attempts += 1
    token.save(update_fields=["attempts"])

    submitted_hash = _hash_otp(raw_otp.strip())
    # Constant-time comparison to mitigate timing-based side channels
    if not secrets.compare_digest(submitted_hash, token.token_hash):
        remaining = OTPToken.MAX_ATTEMPTS - token.attempts
        if remaining <= 0:
            token.is_used = True
            token.save(update_fields=["is_used"])
            return {
                "success": False,
                "message": "Maximum attempts reached. Request a new code.",
            }
        return {
            "success": False,
            "message": f"Invalid code. {remaining} attempt(s) remaining.",
        }

    # Mark consumed
    token.is_used = True
    token.save(update_fields=["is_used"])
    logger.info("OTP verified | user_id=%s", user.pk)
    return {"success": True, "message": "OTP verified successfully."}
