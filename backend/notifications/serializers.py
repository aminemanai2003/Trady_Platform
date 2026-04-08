"""DRF serializers for notifications / 2FA endpoints."""

from rest_framework import serializers


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(
        write_only=True,
        style={"input_type": "password"},
    )


class OTPSendSerializer(serializers.Serializer):
    METHOD_CHOICES = [("email", "Email"), ("sms", "SMS")]
    method = serializers.ChoiceField(choices=METHOD_CHOICES, default="email")


class OTPVerifySerializer(serializers.Serializer):
    otp = serializers.CharField(min_length=6, max_length=6)

    def validate_otp(self, value: str) -> str:
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be exactly 6 digits.")
        return value


class TwoFASetupSerializer(serializers.Serializer):
    METHOD_CHOICES = [("email", "Email"), ("sms", "SMS"), ("face", "Face ID")]

    enabled = serializers.BooleanField()
    preferred_method = serializers.ChoiceField(choices=METHOD_CHOICES, default="email")
    phone_number = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_phone_number(self, value: str) -> str:
        """Require E.164 format when SMS is the preferred method."""
        if not value:
            return value
        if not value.startswith("+") or not value[1:].isdigit():
            raise serializers.ValidationError(
                "Phone number must be in E.164 format, e.g. +33612345678."
            )
        return value

    def validate(self, attrs):
        if attrs.get("enabled") and attrs.get("preferred_method") == "sms" and not attrs.get("phone_number"):
            raise serializers.ValidationError({
                "phone_number": "Phone number is required for SMS 2FA.",
            })
        return attrs


class VerifyTwoFASetupSerializer(serializers.Serializer):
    """Serializer for testing 2FA setup after initial configuration."""
    METHOD_CHOICES = [("email", "Email"), ("sms", "SMS"), ("face", "Face ID")]

    method = serializers.ChoiceField(choices=METHOD_CHOICES)
    otp = serializers.CharField(
        min_length=6,
        max_length=6,
        required=False,
        allow_blank=True,
    )
    image = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    def validate_otp(self, value: str) -> str:
        """Validate OTP format."""
        if not value:
            return value
        value = value.strip()
        if not value.isdigit():
            raise serializers.ValidationError("OTP must be exactly 6 digits.")
        return value

    def validate(self, attrs):
        method = attrs.get("method")
        if method in ("email", "sms") and not attrs.get("otp"):
            raise serializers.ValidationError({
                "otp": f"OTP code is required for {method} verification.",
            })
        if method == "face" and not attrs.get("image"):
            raise serializers.ValidationError({
                "image": "Face image is required for face verification.",
            })
        return attrs
