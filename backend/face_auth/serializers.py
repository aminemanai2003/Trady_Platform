"""DRF serializers for face authentication endpoints."""

from rest_framework import serializers


class FaceEnrollSerializer(serializers.Serializer):
    """
    POST /api/face-auth/enroll/
    Body: one base64-encoded selfie image.
    """

    image = serializers.CharField(
        help_text=(
            "Base64-encoded face image (JPEG or PNG). "
            "Accepts both plain base64 and data-URI prefixed strings "
            "(data:image/jpeg;base64,...)."
        )
    )


class FaceVerifySerializer(serializers.Serializer):
    """
    POST /api/face-auth/verify/
    At minimum one base64 image is required.
    For full liveness validation also supply challenge_id + liveness_frame.
    """

    image = serializers.CharField(
        help_text="Base64-encoded live capture (frame BEFORE the liveness action)."
    )
    challenge_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        default=None,
        help_text="Challenge UUID returned by GET /api/face-auth/liveness/challenge/.",
    )
    liveness_frame = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
        help_text=(
            "Base64-encoded second frame captured DURING / AFTER the liveness action. "
            "Required for full two-frame liveness validation."
        ),
    )
