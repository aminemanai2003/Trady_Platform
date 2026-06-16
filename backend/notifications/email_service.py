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
    # Strip spaces — Google App Passwords are displayed with spaces for readability
    # but SMTP auth requires the 16-character form without spaces.
    if password:
        password = password.replace(" ", "")

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
    # Format OTP as "123 456" for readability in both plain-text and HTML
    otp_display = f"{otp[:3]} {otp[3:]}" if len(otp) == 6 else otp

    subject = "Your Trady verification code"

    body = (
        f"Hi {display_name},\n\n"
        f"Your Trady verification code is: {otp_display}\n\n"
        f"This code expires in 5 minutes. Never share it with anyone.\n\n"
        f"If you did not request this code, please secure your account immediately.\n\n"
        f"— The Trady Security Team"
    )

    html_body = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Trady — Verification Code</title>
</head>
<body style="margin:0;padding:0;background:#0b0f1a;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#0b0f1a;padding:48px 16px;">
    <tr>
      <td align="center">
        <table width="520" cellpadding="0" cellspacing="0" border="0"
               style="background:#111827;border-radius:16px;overflow:hidden;
                      border:1px solid #1e2d45;max-width:520px;width:100%;">

          <!-- Header / Logo band -->
          <tr>
            <td style="background:linear-gradient(135deg,#0658BA 0%,#0a3f7a 100%);
                        padding:32px 40px 28px;text-align:center;">
              <!-- Logo wordmark -->
              <table cellpadding="0" cellspacing="0" border="0" align="center">
                <tr>
                  <td style="background:#fff;border-radius:10px;
                              padding:6px 14px;display:inline-block;">
                    <span style="font-size:22px;font-weight:800;
                                 color:#0658BA;letter-spacing:-0.5px;
                                 font-family:'Segoe UI',Arial,sans-serif;">
                      Trady
                    </span>
                  </td>
                </tr>
              </table>
              <p style="margin:14px 0 0;color:#93c5fd;font-size:13px;
                         letter-spacing:0.05em;text-transform:uppercase;
                         font-weight:600;">
                Security Verification
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:40px 40px 32px;">

              <p style="margin:0 0 8px;color:#9ca3af;font-size:14px;">Hi <strong style="color:#e5e7eb;">{display_name}</strong>,</p>
              <p style="margin:0 0 32px;color:#9ca3af;font-size:14px;line-height:1.6;">
                Use the code below to complete your sign-in to Trady.
                This code is valid for <strong style="color:#e5e7eb;">5 minutes</strong>.
              </p>

              <!-- OTP Box -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td align="center" style="padding:4px 0 36px;">
                    <div style="background:#0b0f1a;border:1px solid #1e3a5f;
                                border-radius:14px;padding:28px 40px;display:inline-block;">
                      <!-- "Your code" label -->
                      <p style="margin:0 0 12px;color:#4d8048;font-size:11px;
                                 font-weight:700;letter-spacing:0.15em;
                                 text-transform:uppercase;text-align:center;">
                        Verification Code
                      </p>
                      <!-- The code itself -->
                      <p style="margin:0;font-size:52px;font-weight:800;
                                 letter-spacing:18px;color:#ffffff;
                                 text-align:center;font-family:'Courier New',monospace;
                                 line-height:1;">
                        {otp_display}
                      </p>
                      <!-- Timer bar -->
                      <p style="margin:16px 0 0;color:#6b7280;font-size:12px;
                                 text-align:center;">
                        ⏱ Expires in <strong style="color:#e5e7eb;">5 minutes</strong>
                      </p>
                    </div>
                  </td>
                </tr>
              </table>

              <!-- Security note -->
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr>
                  <td style="background:#1a1f2e;border-left:3px solid #0658BA;
                              border-radius:0 8px 8px 0;padding:14px 18px;">
                    <p style="margin:0;color:#9ca3af;font-size:12px;line-height:1.5;">
                      🔒 <strong style="color:#e5e7eb;">Never share</strong> this code with anyone —
                      Trady will never ask for it by phone or chat.<br/>
                      If you didn't request this, 
                      <a href="#" style="color:#0658BA;text-decoration:none;">
                        secure your account
                      </a> immediately.
                    </p>
                  </td>
                </tr>
              </table>

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#0d1117;border-top:1px solid #1e2d45;
                        padding:20px 40px;text-align:center;">
              <p style="margin:0;color:#374151;font-size:11px;line-height:1.6;">
                © 2026 Trady · Secure Trading Platform<br />
                This is an automated message — please do not reply.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

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
