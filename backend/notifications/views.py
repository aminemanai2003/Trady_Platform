"""
Authentication + 2FA views.

Login flow
----------
Step 1 — POST /api/auth/login/
   • Validates credentials.
   • If 2FA is disabled: returns an auth token immediately.
   • If 2FA is enabled : stores the pending user ID in the server-side session,
     dispatches an OTP, returns {"requires_2fa": true}.

Step 2 — POST /api/auth/verify-otp/
   • User submits the 6-digit code.
   • On success: clears the pending session entry, returns an auth token.

Auxiliary endpoints
-------------------
POST /api/auth/send-otp/    — (re)send OTP (rate-limited).
GET  /api/auth/2fa/setup/   — read current 2FA settings (authenticated).
POST /api/auth/2fa/setup/   — enable/disable 2FA and set method (authenticated).
"""

import logging

from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import UserTwoFAProfile
from .otp_service import generate_and_send_otp, verify_otp
from .serializers import (
    LoginSerializer,
    OTPSendSerializer,
    OTPVerifySerializer,
    TwoFASetupSerializer,
    VerifyTwoFASetupSerializer,
)
from .throttles import LoginThrottle, OTPRequestThrottle, OTPVerifyThrottle, TwoFAVerifySetupThrottle

logger = logging.getLogger(__name__)

# Session key that holds the pending (pre-2FA) user ID
_SESSION_PENDING_USER = "pending_2fa_user_id"


def _get_client_ip(request) -> str:
    """Extract the real client IP, respecting X-Forwarded-For if present."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


# ── Step 1: credential verification ──────────────────────────────────────────

class LoginView(APIView):
    """
    POST /api/auth/login/

    Body: {"username": "…", "password": "…"}

    Response (no 2FA):
        {"success": true, "requires_2fa": false, "token": "…", "user": {…}}

    Response (2FA enabled):
        {"success": true, "requires_2fa": true, "method": "email"|"sms",
         "message": "OTP sent. Please verify to complete login."}
    """
    permission_classes = [AllowAny]
    throttle_classes = [LoginThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )

        if user is None:
            logger.warning(
                "Failed login | username=%s ip=%s",
                serializer.validated_data["username"],
                _get_client_ip(request),
            )
            return Response(
                {"success": False, "message": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        profile: UserTwoFAProfile | None = getattr(user, "twofa_profile", None)

        # ── Face recognition 2FA ──────────────────────────────────────────────
        if profile and profile.twofa_enabled and profile.preferred_method == UserTwoFAProfile.METHOD_FACE:
            request.session[_SESSION_PENDING_USER] = user.pk
            request.session.save()
            logger.info(
                "Login pending (face 2FA) | user_id=%s ip=%s", user.pk, _get_client_ip(request)
            )
            return Response({
                "success":      True,
                "requires_2fa": True,
                "method":       "face",
                "message":      "Please complete face verification to sign in.",
            })

        # ── OTP 2FA (email / SMS) ─────────────────────────────────────────────
        if profile and profile.twofa_enabled and profile.preferred_method in ("email", "sms"):
            # Store pending user ID in the server-side session (NOT the response body)
            request.session[_SESSION_PENDING_USER] = user.pk
            request.session.save()

            result = generate_and_send_otp(
                user,
                profile.preferred_method,
                session_key=request.session.session_key,
            )
            if not result["success"]:
                del request.session[_SESSION_PENDING_USER]
                request.session.save()
                return Response(
                    {"success": False, "message": result["message"]},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            return Response({
                "success": True,
                "requires_2fa": True,
                "method": profile.preferred_method,
                "message": "OTP sent. Please verify to complete login.",
            })

        # No 2FA — issue token directly
        token, _ = Token.objects.get_or_create(user=user)
        logger.info("Login success (no 2FA) | user_id=%s ip=%s", user.pk, _get_client_ip(request))
        return Response({
            "success": True,
            "requires_2fa": False,
            "token": token.key,
            "user": {"id": user.pk, "username": user.username, "email": user.email},
        })


# ── Step 2: OTP verification ──────────────────────────────────────────────────

class VerifyOTPView(APIView):
    """
    POST /api/auth/verify-otp/

    Body: {"otp": "123456"}

    Requires an active session created by LoginView (pending_2fa_user_id must exist).

    Response (success):
        {"success": true, "token": "…", "user": {…}}

    Response (failure):
        {"success": false, "message": "…"}
    """
    permission_classes = [AllowAny]
    throttle_classes = [OTPVerifyThrottle]

    def post(self, request):
        serializer = OTPVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        pending_user_id = request.session.get(_SESSION_PENDING_USER)
        if not pending_user_id:
            return Response(
                {"success": False, "message": "No pending authentication. Please log in first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=pending_user_id)
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "Session expired. Please log in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        result = verify_otp(
            user,
            serializer.validated_data["otp"],
            session_key=request.session.session_key,
        )

        if not result["success"]:
            return Response(
                {"success": False, "message": result["message"]},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        # OTP verified — clear the pending entry and complete the login
        del request.session[_SESSION_PENDING_USER]
        request.session.save()

        token, _ = Token.objects.get_or_create(user=user)
        logger.info("2FA verified — login success | user_id=%s ip=%s", user.pk, _get_client_ip(request))
        return Response({
            "success": True,
            "token": token.key,
            "user": {"id": user.pk, "username": user.username, "email": user.email},
        })


# ── Resend OTP ────────────────────────────────────────────────────────────────

class SendOTPView(APIView):
    """
    POST /api/auth/send-otp/

    (Re)send an OTP to the pending user.  Rate-limited to 5 requests / 10 min.

    Optional body: {"method": "email"|"sms"}
    """
    permission_classes = [AllowAny]
    throttle_classes = [OTPRequestThrottle]

    def post(self, request):
        pending_user_id = request.session.get(_SESSION_PENDING_USER)
        if not pending_user_id:
            return Response(
                {"success": False, "message": "No pending authentication."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user = User.objects.get(pk=pending_user_id)
        except User.DoesNotExist:
            return Response(
                {"success": False, "message": "Session expired. Please log in again."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = OTPSendSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        profile: UserTwoFAProfile | None = getattr(user, "twofa_profile", None)
        # Honour the user's configured preferred method; fall back to request param
        method = (
            profile.preferred_method
            if profile and profile.preferred_method in ("email", "sms")
            else serializer.validated_data.get("method", "email")
        )

        result = generate_and_send_otp(user, method, session_key=request.session.session_key)
        code = status.HTTP_200_OK if result["success"] else status.HTTP_503_SERVICE_UNAVAILABLE
        return Response(result, status=code)


# ── 2FA setup (authenticated) ─────────────────────────────────────────────────

class TwoFASetupView(APIView):
    """
    GET  /api/auth/2fa/setup/  — retrieve current 2FA configuration.
    POST /api/auth/2fa/setup/  — update 2FA settings.

    Requires authentication (Token or Session).
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        profile: UserTwoFAProfile | None = getattr(request.user, "twofa_profile", None)
        if not profile:
            return Response({
                "twofa_enabled": False,
                "preferred_method": "email",
                "phone_number": "",
            })
        return Response({
            "twofa_enabled": profile.twofa_enabled,
            "preferred_method": profile.preferred_method,
            "phone_number": profile.phone_number,
        })

    def post(self, request):
        serializer = TwoFASetupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        profile, _ = UserTwoFAProfile.objects.get_or_create(user=request.user)
        profile.twofa_enabled = data["enabled"]
        profile.preferred_method = data["preferred_method"]
        if data.get("phone_number"):
            profile.phone_number = data["phone_number"]
        profile.save()

        status_str = "enabled" if profile.twofa_enabled else "disabled"
        logger.info(
            "2FA %s | user_id=%s method=%s",
            status_str, request.user.pk, profile.preferred_method,
        )
        return Response({"success": True, "message": f"Two-factor authentication {status_str}."})


# ── Verify 2FA Setup (post-setup test) ───────────────────────────────────────

class VerifyTwoFASetupView(APIView):
    """
    POST /api/auth/verify-2fa-setup/

    Test the 2FA method after initial setup to ensure it works.
    Requires authentication (Token or Session).

    Body (for face):
        {"method": "face", "image": "<base64>"}

    Body (for email/sms):
        {"method": "email"|"sms", "otp": "123456"}

    Response (success):
        {"success": true, "verified": true, "message": "..."}

    Response (failure):
        {"success": false, "verified": false, "message": "...", "detail": "..."}
    """
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [IsAuthenticated]
    throttle_classes = [TwoFAVerifySetupThrottle]

    def post(self, request):
        serializer = VerifyTwoFASetupSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        method = serializer.validated_data["method"]
        user = request.user

        # ── Face verification ─────────────────────────────────────────────────
        if method == "face":
            from face_auth.auth_integration import verify_face  # noqa: PLC0415

            b64_image = serializer.validated_data["image"]
            result = verify_face(user, b64_image)

            if result["verified"]:
                logger.info(
                    "2FA setup test (face) success | user_id=%s confidence=%.4f",
                    user.pk, result.get("confidence", 0.0),
                )
                return Response({
                    "success": True,
                    "verified": True,
                    "message": "Face verification successful.",
                    "confidence": result.get("confidence", 0.0),
                })
            else:
                logger.warning(
                    "2FA setup test (face) failed | user_id=%s reason=%s",
                    user.pk, result.get("reason", "unknown"),
                )
                return Response({
                    "success": False,
                    "verified": False,
                    "message": "Face verification failed.",
                    "reason": result.get("reason", "no_match"),
                    "detail": result.get("detail", "Face did not match enrollment."),
                }, status=status.HTTP_400_BAD_REQUEST)

        # ── OTP verification (email / SMS) ────────────────────────────────────
        elif method in ("email", "sms"):
            otp_code = serializer.validated_data["otp"]

            # Verify the OTP using existing otp_service logic
            result = verify_otp(
                user,
                otp_code,
                session_key=request.session.session_key or "",
            )

            if result["success"]:
                logger.info(
                    "2FA setup test (%s) success | user_id=%s",
                    method, user.pk,
                )
                return Response({
                    "success": True,
                    "verified": True,
                    "message": f"{method.upper()} verification successful.",
                })
            else:
                logger.warning(
                    "2FA setup test (%s) failed | user_id=%s",
                    method, user.pk,
                )
                return Response({
                    "success": False,
                    "verified": False,
                    "message": result["message"],
                }, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {"success": False, "message": "Invalid method."},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ── Django User Registration (called by Next.js after Prisma registration) ────

class DjangoRegisterView(APIView):
    """
    POST /api/auth/django-register/

    Creates (or reuses) a Django User for the given email, issues a DRF auth
    token.  Called by the Next.js registration flow after the Prisma/NextAuth
    user has already been created.

    Body:   {"email": "...", "password": "..."}

    Response (success):
        {"success": true, "token": "...", "user": {"id": ..., "username": ..., "email": ...}}

    Response (error):
        {"success": false, "message": "..."}
    """
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        password = request.data.get("password", "")

        if not email or not password:
            return Response(
                {"success": False, "message": "Email and password are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Use email as Django username (truncated to model max_length=150)
        username = email[:150]

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )

        # Always sync the password so it matches the NextAuth account
        user.set_password(password)
        user.save(update_fields=["password"])

        token, _ = Token.objects.get_or_create(user=user)

        logger.info(
            "Django user %s | user_id=%s ip=%s",
            "created" if created else "re-linked",
            user.pk,
            _get_client_ip(request),
        )
        return Response({
            "success": True,
            "token": token.key,
            "user": {"id": user.pk, "username": user.username, "email": user.email},
        })
