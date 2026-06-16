"""
SMS notification service via Twilio REST API.

Required environment variables:
  TWILIO_ACCOUNT_SID   Your Twilio Account SID (starts with "AC…")
  TWILIO_AUTH_TOKEN    Your Twilio Auth Token
  TWILIO_PHONE_NUMBER  Your Twilio sender number in E.164 format (e.g. +14155552671)

Security notes:
  - Credentials are read exclusively from environment variables.
  - twilio is an optional dependency; import is deferred to avoid hard crashes
    when the package is absent and SMS is not in use.
  - Auth token is NEVER logged; only delivery SID and status are emitted.
"""

import logging
import os

logger = logging.getLogger(__name__)


# ── Core transport ────────────────────────────────────────────────────────────

def send_sms(to: str, message: str) -> bool:
    """
    Send an SMS via Twilio.

    Args:
        to:      Recipient phone number in E.164 format (e.g. '+33612345678').
        message: SMS text body.  Keep under 160 chars for a single segment.

    Returns:
        True on success, False on any failure.
    """
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    auth_token = os.getenv("TWILIO_AUTH_TOKEN")
    from_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not all([account_sid, auth_token, from_number]):
        logger.error(
            "SMS service not configured: one or more Twilio environment variables missing "
            "(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER)."
        )
        return False

    try:
        from twilio.rest import Client  # lazy import — avoid hard dependency
    except ImportError:
        logger.error("twilio package is not installed. Run: pip install twilio")
        return False

    try:
        client = Client(account_sid, auth_token)  # credentials never logged
        sms = client.messages.create(
            body=message,
            from_=from_number,
            to=to,
        )
        logger.info("SMS delivered | to=%s sid=%s status=%s", to, sms.sid, sms.status)
        return True

    except Exception as exc:  # noqa: BLE001
        # Deliberately broad: Twilio raises many SDK-specific exception classes.
        # We log only the exception class name, NOT the message, to avoid
        # accidentally emitting auth credentials embedded in some error strings.
        logger.error(
            "Twilio error sending SMS to %s: %s",
            to,
            type(exc).__name__,
        )
        return False


# ── High-level helpers ────────────────────────────────────────────────────────

def send_otp_sms(to: str, otp: str) -> bool:
    """
    Send a 6-digit OTP via SMS.

    The raw OTP value is embedded in the SMS body but NEVER written to logs.
    """
    message = (
        f"Your verification code is: {otp}\n"
        f"Valid for 5 minutes. Do not share it with anyone."
    )
    return send_sms(to, message)


def send_login_alert_sms(to: str, ip_address: str) -> bool:
    """Send a security alert SMS for a suspicious or new login."""
    message = (
        f"New sign-in on your account from {ip_address}. "
        f"If this wasn't you, change your password immediately."
    )
    return send_sms(to, message)
