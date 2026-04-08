"""
Email notification service — Gmail SMTP (TLS, port 587).

Required environment variables:
  GMAIL_USER          Gmail sender address (e.g. you@gmail.com)
  GMAIL_APP_PASSWORD  Google App Password (NOT your regular password).
                      Generate at: myaccount.google.com → Security → App passwords

Security notes:
  - Credentials are read exclusively from environment variables.
  - Raw OTP values are never logged; only delivery status is emitted.
  - SMTP connection uses STARTTLS — plaintext is never transmitted.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 587


# ── Core transport ────────────────────────────────────────────────────────────

def send_email(
    to: str,
    subject: str,
    body: str,
    html_body: str | None = None,
) -> bool:
    """
    Send a single email via Gmail SMTP with STARTTLS.

    Args:
        to:        Recipient e-mail address.
        subject:   Subject line.
        body:      Plain-text fallback body (always included).
        html_body: Optional HTML body; produces a multipart/alternative message.

    Returns:
        True on success, False on any failure.
    """
    sender = os.getenv("GMAIL_USER")
    password = os.getenv("GMAIL_APP_PASSWORD")

    if not sender or not password:
        logger.error(
            "Email service not configured: GMAIL_USER or GMAIL_APP_PASSWORD missing."
        )
        return False

    if html_body:
        msg: MIMEMultipart = MIMEMultipart("alternative")
    else:
        msg = MIMEMultipart()

    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))
    if html_body:
        msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(_SMTP_HOST, _SMTP_PORT, timeout=10) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender, password)  # credentials never logged
            server.sendmail(sender, [to], msg.as_string())
        logger.info("Email delivered | to=%s subject=%s", to, subject)
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail SMTP authentication failed — verify GMAIL_APP_PASSWORD is a valid App Password."
        )
    except smtplib.SMTPRecipientsRefused:
        logger.error("Email rejected for recipient: %s", to)
    except smtplib.SMTPException as exc:
        logger.error("SMTP error while sending to %s: %s", to, exc)
    except OSError as exc:
        logger.error("Network error connecting to Gmail SMTP: %s", exc)

    return False


# ── High-level helpers ────────────────────────────────────────────────────────

def send_otp_email(to: str, otp: str, username: str = "") -> bool:
    """
    Send a 6-digit OTP verification code by email.

    The raw OTP value is embedded in the email body but NEVER written to logs.
    """
    display_name = username or "there"
    subject = "Your verification code"
    body = (
        f"Hi {display_name},\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code expires in 5 minutes. Never share it with anyone.\n\n"
        f"If you did not request this code, please secure your account immediately."
    )
    html_body = f"""
<div style="font-family:Arial,sans-serif;max-width:500px;margin:auto;padding:28px;
            border:1px solid #e5e7eb;border-radius:10px;">
  <h2 style="margin:0 0 16px;color:#111827;">Verification Code</h2>
  <p style="color:#374151;">Hi <strong>{display_name}</strong>,</p>
  <p style="color:#374151;">Use the code below to complete your sign-in:</p>
  <div style="background:#f3f4f6;padding:20px 32px;border-radius:8px;
              text-align:center;font-size:36px;letter-spacing:10px;
              font-weight:700;color:#111827;margin:24px 0;">
    {otp}
  </div>
  <p style="color:#374151;">This code is valid for <strong>5 minutes</strong>.</p>
  <p style="color:#6b7280;font-size:12px;margin-top:24px;">
    If you did not request this, you can safely ignore this email.
  </p>
</div>
"""
    return send_email(to, subject, body, html_body)


def send_login_alert_email(
    to: str,
    username: str,
    ip_address: str,
    user_agent: str = "",
) -> bool:
    """Send a security alert for a new login detected on the account."""
    subject = "New sign-in detected on your account"
    device_info = user_agent[:120] if user_agent else "Unknown device"
    body = (
        f"Hi {username},\n\n"
        f"A new sign-in was detected on your account.\n"
        f"  IP address : {ip_address}\n"
        f"  Device     : {device_info}\n\n"
        f"If this was you, no further action is needed.\n"
        f"If this was NOT you, change your password immediately."
    )
    return send_email(to, subject, body)
