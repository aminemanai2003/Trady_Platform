"""
Django models for face authentication.

  UserFaceProfile       — one-to-one extension of User; stores the
                          Fernet-encrypted face embedding vector.

  FaceLivenessChallenge — single-use liveness challenge token, expires in
                          2 minutes and is bound to the originating session.
"""

import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserFaceProfile(models.Model):
    """
    Stores the encrypted face embedding for a user.

    Security notes:
      - The raw embedding vector is NEVER persisted in plaintext.
      - embedding_enc holds a Fernet-encrypted JSON array (see crypto.py).
      - failed_attempts is incremented on each failed verification and reset
        on success; when it reaches 5, face auth for the account is locked
        until an admin or OTP-based re-enrollment resets it.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="face_profile",
    )
    # Fernet(AES-128-CBC)-encrypted JSON list of floats
    embedding_enc = models.TextField(
        help_text="Fernet-encrypted face embedding vector. Do not edit manually."
    )
    is_active = models.BooleanField(default=True)
    failed_attempts = models.PositiveSmallIntegerField(default=0)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Face Profile"
        verbose_name_plural = "User Face Profiles"

    def __str__(self) -> str:
        return (
            f"FaceProfile(user={self.user.username}, "
            f"active={self.is_active}, fails={self.failed_attempts})"
        )


class FaceLivenessChallenge(models.Model):
    """
    A single-use liveness challenge token.

    Created when the client calls GET /api/face-auth/liveness/challenge/.
    Must be submitted (with two frames) within CHALLENGE_EXPIRY_MIN minutes.
    """

    ACTION_BLINK  = "blink"
    ACTION_MOTION = "motion"
    ACTION_CHOICES = [
        (ACTION_BLINK,  "Blink"),
        (ACTION_MOTION, "Head motion"),
    ]

    challenge_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    # Optional user FK — null when challenge is issued before login completes
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="liveness_challenges",
    )
    action      = models.CharField(max_length=16, choices=ACTION_CHOICES)
    session_key = models.CharField(max_length=64, blank=True, default="")
    is_used     = models.BooleanField(default=False, db_index=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    expires_at  = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["is_used", "expires_at"]),
        ]

    def __str__(self) -> str:
        return (
            f"LivenessChallenge({self.challenge_id!s:.8}, "
            f"action={self.action}, used={self.is_used})"
        )
