"""URL patterns for face authentication endpoints."""

from django.urls import path

try:
    from .views import FaceEnrollView, FaceVerifyView, LivenessChallengeView
except Exception:  # optional heavy deps (opencv/deepface) may be missing
    from rest_framework.permissions import AllowAny
    from rest_framework.response import Response
    from rest_framework.views import APIView

    class _DepsMissingView(APIView):
        permission_classes = [AllowAny]

        def post(self, request, *args, **kwargs):
            return Response(
                {
                    "error": "Face auth dependencies are not installed on this machine.",
                    "hint": "Install backend requirements (opencv/deepface) to enable face-auth endpoints.",
                },
                status=503,
            )

        def get(self, request, *args, **kwargs):
            return self.post(request, *args, **kwargs)

    FaceEnrollView = _DepsMissingView
    FaceVerifyView = _DepsMissingView
    LivenessChallengeView = _DepsMissingView

urlpatterns = [
    # Enroll / re-enroll a face (requires auth token)
    path("enroll/", FaceEnrollView.as_view(), name="face-enroll"),

    # Get a liveness challenge token before capture
    path("liveness/challenge/", LivenessChallengeView.as_view(), name="face-liveness-challenge"),

    # Verify a live selfie (completes 2FA login if session is pending)
    path("verify/", FaceVerifyView.as_view(), name="face-verify"),
]
