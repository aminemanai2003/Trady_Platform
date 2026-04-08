"""
Face authentication API views — powered by DeepFace.

Endpoints
---------
POST /api/face-auth/enroll/
    Enroll or re-enroll the authenticated user's face.
    Requires a DRF auth token (Authorization: Token <key>).

GET  /api/face-auth/liveness/challenge/
    Issue a single-use liveness challenge token + instruction.
    No authentication required (called during the login 2FA flow).

POST /api/face-auth/verify/
    Verify a live selfie against the stored enrollment.

    Two operating modes:
      A. Pending 2FA session  — completes login, returns a DRF token.
      B. Authenticated user   — returns verification result only.

All views are thin wrappers around auth_integration / face_service.
Face detection, embedding extraction, and comparison are handled by DeepFace.
"""

import logging

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .auth_integration import complete_face_login, enroll_face, verify_face
from .face_detection import decode_b64_image  # kept for liveness two-frame decode
from .liveness_detection import generate_challenge, validate_challenge
from .models import UserFaceProfile
from .serializers import FaceEnrollSerializer, FaceVerifySerializer
from .throttles import FaceEnrollThrottle, FaceVerifyThrottle
from .validation import validate_enroll_request, validate_verify_request

logger = logging.getLogger(__name__)

_SESSION_PENDING_USER = "pending_2fa_user_id"
_MAX_FAILED_ATTEMPTS  = 5


def _get_client_ip(request) -> str:
    xff = request.META.get("HTTP_X_FORWARDED_FOR", "")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR", "unknown")


# ── Enrollment ────────────────────────────────────────────────────────────────

class FaceEnrollView(APIView):
    """
    POST /api/face-auth/enroll/

    Body:   {"image": "<base64>"}
    Success:  {"success": true,  "message": "..."}
    Failure:  {"success": false, "reason": "...", "detail": "..."}
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes     = [IsAuthenticated]
    throttle_classes       = [FaceEnrollThrottle]

    def post(self, request):
        v = validate_enroll_request(request.data)
        if not v["valid"]:
            return Response(
                {"success": False, "reason": v["reason"], "detail": v["detail"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = enroll_face(request.user, v["image"])

        if not result["ok"]:
            http_status = (
                status.HTTP_503_SERVICE_UNAVAILABLE
                if result["reason"] == "system_error"
                else status.HTTP_400_BAD_REQUEST
            )
            return Response(
                {"success": False, "reason": result["reason"], "detail": result["detail"]},
                status=http_status,
            )

        logger.info("Face enroll success | user_id=%s ip=%s", request.user.pk, _get_client_ip(request))
        return Response({"success": True, "message": result["message"]})


# ── Liveness challenge ────────────────────────────────────────────────────────

class LivenessChallengeView(APIView):
    """
    GET /api/face-auth/liveness/challenge/

    Issue a new single-use liveness challenge.
    No authentication required (used during the login 2FA flow).

    Response:
        {
            "challenge_id": "<uuid>",
            "action":       "blink" | "motion",
            "instruction":  "<human-readable>",
            "expires_at":   "<ISO 8601>",
        }
    """
    permission_classes = [AllowAny]
    throttle_classes = [FaceVerifyThrottle]

    def get(self, request):
        session_key = request.session.session_key or ""
        challenge = generate_challenge(session_key=session_key)
        return Response(challenge)


# ── Verification ──────────────────────────────────────────────────────────────

class FaceVerifyView(APIView):
    """
    POST /api/face-auth/verify/

    Body:
        {
            "image":          "<base64>",
            "challenge_id":   "<uuid>",     // optional liveness challenge
            "liveness_frame": "<base64>",   // optional second frame
        }

    Success (2FA login):   {"verified": true, "confidence": 0.97, "reason": "match",
                            "token": "...", "user": {...}}
    Success (re-verify):   {"verified": true, "confidence": 0.97, "reason": "match"}
    Failure:               {"verified": false, "reason": "...", "fallback_available": true}
    """
    permission_classes = [AllowAny]
    throttle_classes   = [FaceVerifyThrottle]

    def post(self, request):
        v = validate_verify_request(request.data)
        if not v["valid"]:
            return Response(
                {"verified": False, "confidence": 0.0,
                 "reason": v["reason"], "detail": v["detail"]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Resolve user ──────────────────────────────────────────────────────
        user: User | None = None
        is_completing_2fa = False

        pending_id = request.session.get(_SESSION_PENDING_USER)
        if pending_id:
            try:
                user = User.objects.get(pk=pending_id)
                is_completing_2fa = True
            except User.DoesNotExist:
                return Response(
                    {"verified": False, "confidence": 0.0, "reason": "no_match",
                     "detail": "Session expired. Please log in again."},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
        elif request.user.is_authenticated:
            user = request.user
        else:
            return Response(
                {"verified": False, "confidence": 0.0, "reason": "no_match",
                 "detail": "No active session found. Please initiate login first."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # ── Optional two-frame liveness check ─────────────────────────────────
        challenge_id = v.get("challenge_id", "")
        liveness_b64 = v.get("liveness_frame", "")

        if challenge_id and liveness_b64:
            try:
                frame1 = decode_b64_image(v["image"])
                frame2 = decode_b64_image(liveness_b64)
            except ValueError as exc:
                return Response(
                    {"verified": False, "confidence": 0.0,
                     "reason": "invalid_image", "detail": str(exc)},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            liveness = validate_challenge(
                challenge_id, frame1, frame2,
                session_key=request.session.session_key or "",
            )
            if not liveness["passed"]:
                logger.warning(
                    "Liveness challenge failed | user_id=%s ip=%s reason=%s",
                    user.pk, _get_client_ip(request), liveness["reason"],
                )
                return Response(
                    {"verified": False, "confidence": 0.0,
                     "reason": liveness["reason"], "detail": liveness["detail"]},
                    status=status.HTTP_403_FORBIDDEN,
                )

        # ── Face verification (DeepFace) ──────────────────────────────────────
        result = verify_face(user, v["image"])

        if not result["verified"]:
            http_status = (
                status.HTTP_403_FORBIDDEN
                if result["reason"] == "locked"
                else status.HTTP_401_UNAUTHORIZED
            )
            logger.warning(
                "Face verify failed | user_id=%s ip=%s reason=%s",
                user.pk, _get_client_ip(request), result["reason"],
            )
            return Response(
                {
                    "verified":           False,
                    "confidence":         result.get("confidence", 0.0),
                    "reason":             result["reason"],
                    "detail":             result.get("detail", ""),
                    "fallback_available": result.get("fallback_available", False),
                },
                status=http_status,
            )

        logger.info(
            "Face verify success | user_id=%s ip=%s confidence=%.4f",
            user.pk, _get_client_ip(request), result["confidence"],
        )

        base_response = {
            "verified":   True,
            "confidence": result["confidence"],
            "reason":     "match",
        }

        if is_completing_2fa:
            login_data = complete_face_login(user, request)
            return Response({**base_response, **login_data})

        return Response(base_response)
