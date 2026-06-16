"""Rate-limiting throttles for face authentication endpoints."""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class FaceEnrollThrottle(UserRateThrottle):
    """
    5 enrollment / re-enrollment requests per hour per authenticated user.
    Prevents brute-force embedding replacement attacks.
    """
    scope = "face_enroll"


class FaceVerifyThrottle(AnonRateThrottle):
    """
    10 face verification or challenge requests per 10 minutes per IP.
    Applied before session-lookup so it covers unauthenticated login flow too.
    """
    scope = "face_verify"
