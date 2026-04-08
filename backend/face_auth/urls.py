"""URL patterns for face authentication endpoints."""

from django.urls import path

from .views import FaceEnrollView, FaceVerifyView, LivenessChallengeView

urlpatterns = [
    # Enroll / re-enroll a face (requires auth token)
    path("enroll/", FaceEnrollView.as_view(), name="face-enroll"),

    # Get a liveness challenge token before capture
    path("liveness/challenge/", LivenessChallengeView.as_view(), name="face-liveness-challenge"),

    # Verify a live selfie (completes 2FA login if session is pending)
    path("verify/", FaceVerifyView.as_view(), name="face-verify"),
]
