"""Initial migration for notifications app."""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserTwoFAProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("twofa_enabled", models.BooleanField(default=False)),
                ("preferred_method", models.CharField(
                    choices=[("email", "Email"), ("sms", "SMS"), ("totp", "Authenticator App (TOTP)")],
                    default="email",
                    max_length=10,
                )),
                ("phone_number", models.CharField(blank=True, default="", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="twofa_profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name": "User 2FA Profile",
                "verbose_name_plural": "User 2FA Profiles",
            },
        ),
        migrations.CreateModel(
            name="OTPToken",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token_hash", models.CharField(max_length=64)),
                ("delivery_method", models.CharField(
                    choices=[("email", "Email"), ("sms", "SMS")],
                    max_length=10,
                )),
                ("session_key", models.CharField(blank=True, default="", max_length=64)),
                ("attempts", models.PositiveSmallIntegerField(default=0)),
                ("is_used", models.BooleanField(db_index=True, default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("user", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="otp_tokens",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="otptoken",
            index=models.Index(fields=["user", "is_used", "expires_at"], name="notif_otp_user_idx"),
        ),
    ]
