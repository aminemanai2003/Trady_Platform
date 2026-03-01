"""URL configuration for FX Alpha Platform."""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("data.urls")),
    path("api/", include("signals.urls")),
    path("api/", include("agents.urls")),
    path("api/", include("analytics.urls")),
    path("api/", include("api.urls_v2")),  # V2 Architecture endpoints
]
