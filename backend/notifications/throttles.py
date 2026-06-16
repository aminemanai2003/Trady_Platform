"""Rate-limiting throttles for authentication and OTP endpoints."""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class LoginThrottle(AnonRateThrottle):
    """
    5 login attempts per minute per IP address.
    Applies to unauthenticated requests at POST /api/auth/login/.
    Rate is configured in settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["login"].
    """
    scope = "login"


class OTPRequestThrottle(UserRateThrottle):
    """
    5 OTP send requests per 10 minutes per user.
    Applies to POST /api/auth/send-otp/.
    """
    scope = "otp_request"


class OTPVerifyThrottle(AnonRateThrottle):
    """
    10 OTP verification attempts per 10 minutes per IP.
    Uses IP-based throttle (user is not yet authenticated at verification time).
    """
    scope = "otp_verify"


class TwoFAVerifySetupThrottle(UserRateThrottle):
    """
    5 2FA setup verification attempts per 10 minutes per user.
    Applies to POST /api/auth/verify-2fa-setup/.
    """
    scope = "twofa_verify_setup"
