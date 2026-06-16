"""
Django models for the notifications / 2FA app.

  UserTwoFAProfile  — one-to-one extension of Django's built-in User:
                      stores 2FA toggle, preferred delivery method, phone number.

  OTPToken          — time-limited, single-use token record:
                      stores the SHA-256 hash of the OTP (never the plaintext),
                      expiry timestamp, attempt counter, and used flag.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserTwoFAProfile(models.Model):
    """Extends Django User with 2FA preferences (one-to-one)."""

    METHOD_EMAIL = "email"
    METHOD_SMS   = "sms"
    METHOD_TOTP  = "totp"
    METHOD_FACE  = "face"
    METHOD_CHOICES = [
        (METHOD_EMAIL, "Email"),
        (METHOD_SMS,   "SMS"),
        (METHOD_TOTP,  "Authenticator App (TOTP)"),
        (METHOD_FACE,  "Face Recognition"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="twofa_profile",
    )
    twofa_enabled = models.BooleanField(default=False)
    preferred_method = models.CharField(
        max_length=10,
        choices=METHOD_CHOICES,
        default=METHOD_EMAIL,
    )
    # E.164 format expected (e.g. +33612345678). Stored as plain text —
    # encrypt at the DB / storage layer if PII regulations apply.
    phone_number = models.CharField(max_length=20, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User 2FA Profile"
        verbose_name_plural = "User 2FA Profiles"

    def __str__(self) -> str:
        return f"2FA({self.user.username}, enabled={self.twofa_enabled}, method={self.preferred_method})"


class OTPToken(models.Model):
    """
    Single-use, time-limited OTP record.

    The raw OTP is NEVER stored.  Only its SHA-256 digest is persisted so that
    a database breach cannot reveal valid codes.
    """

    DELIVERY_EMAIL = "email"
    DELIVERY_SMS = "sms"
    DELIVERY_CHOICES = [
        (DELIVERY_EMAIL, "Email"),
        (DELIVERY_SMS, "SMS"),
    ]

    # Security constants
    EXPIRY_MINUTES: int = 5
    MAX_ATTEMPTS: int = 5

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="otp_tokens",
    )
    # SHA-256 hex digest of the raw 6-digit OTP
    token_hash = models.CharField(max_length=64, db_index=False)
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_CHOICES)
    # Ties the OTP to the Django session that requested it; empty string = no binding
    session_key = models.CharField(max_length=64, blank=True, default="")
    attempts = models.PositiveSmallIntegerField(default=0)
    is_used = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["user", "is_used", "expires_at"]),
        ]
        ordering = ["-created_at"]

    def save(self, *args, **kwargs) -> None:
        # Set expiry only on creation
        if not self.pk:
            self.expires_at = timezone.now() + timedelta(minutes=self.EXPIRY_MINUTES)
        super().save(*args, **kwargs)

    # ── Computed properties ───────────────────────────────────────────────────

    @property
    def is_expired(self) -> bool:
        return timezone.now() > self.expires_at

    @property
    def is_exhausted(self) -> bool:
        return self.attempts >= self.MAX_ATTEMPTS

    def __str__(self) -> str:
        return (
            f"OTPToken(user={self.user.username}, method={self.delivery_method}, "
            f"used={self.is_used}, expires={self.expires_at:%Y-%m-%d %H:%M})"
        )
