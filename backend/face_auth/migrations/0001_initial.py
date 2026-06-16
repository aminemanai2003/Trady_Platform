"""Initial migration for face_auth app."""

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserFaceProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("embedding_enc", models.TextField(
                    help_text="Fernet-encrypted face embedding vector. Do not edit manually."
                )),
                ("is_active",        models.BooleanField(default=True)),
                ("failed_attempts",  models.PositiveSmallIntegerField(default=0)),
                ("enrolled_at",      models.DateTimeField(auto_now_add=True)),
                ("updated_at",       models.DateTimeField(auto_now=True)),
                ("user", models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="face_profile",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "verbose_name":        "User Face Profile",
                "verbose_name_plural": "User Face Profiles",
            },
        ),
        migrations.CreateModel(
            name="FaceLivenessChallenge",
            fields=[
                ("challenge_id", models.UUIDField(
                    primary_key=True, default=uuid.uuid4, editable=False, serialize=False
                )),
                ("action",      models.CharField(
                    max_length=16,
                    choices=[("blink", "Blink"), ("motion", "Head motion")],
                )),
                ("session_key", models.CharField(blank=True, default="", max_length=64)),
                ("is_used",     models.BooleanField(db_index=True, default=False)),
                ("created_at",  models.DateTimeField(auto_now_add=True)),
                ("expires_at",  models.DateTimeField()),
                ("user", models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="liveness_challenges",
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.AddIndex(
            model_name="facelivenessChallenge",
            index=models.Index(
                fields=["is_used", "expires_at"],
                name="face_liveness_idx",
            ),
        ),
    ]
