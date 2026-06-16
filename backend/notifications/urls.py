"""URL patterns for authentication + 2FA endpoints."""

from django.urls import path

from .views import (
    DjangoRegisterView,
    LoginView,
    SendOTPView,
    TwoFASetupView,
    VerifyOTPView,
    VerifyTwoFASetupView,
)

urlpatterns = [
    # Step 1: credential verification
    path("login/", LoginView.as_view(), name="auth-login"),

    # Step 2: OTP submission (after 2FA required)
    path("verify-otp/", VerifyOTPView.as_view(), name="auth-verify-otp"),

    # Resend OTP (rate-limited)
    path("send-otp/", SendOTPView.as_view(), name="auth-send-otp"),

    # 2FA settings management (authenticated users only)
    path("2fa/setup/", TwoFASetupView.as_view(), name="auth-2fa-setup"),

    # Verify 2FA setup after initial configuration (authenticated users only)
    path("verify-2fa-setup/", VerifyTwoFASetupView.as_view(), name="auth-verify-2fa-setup"),

    # Register Django user after Next.js / Prisma registration
    path("django-register/", DjangoRegisterView.as_view(), name="auth-django-register"),
]
