"""URL configuration for FX Alpha Platform."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("data.urls")),
    path("api/", include("signals.urls")),
    path("api/", include("agents.urls")),
    path("api/", include("analytics.urls")),
    path("api/", include("api.urls_v2")),             # V2 Architecture endpoints
    path("api/ocr/", include("ocr.urls")),            # OCR extraction pipeline
    path("api/auth/", include("notifications.urls")), # Login + OTP 2FA endpoints
    path("api/face-auth/", include("face_auth.urls")), # Face recognition 2FA
    path("api/tutor/",     include("rag_tutor.urls")),  # RAG Strategy Tutor
]
