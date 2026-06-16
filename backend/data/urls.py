"""URL routing for data app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .calendar_views import economic_calendar, technical_indicators

router = DefaultRouter()
router.register(r"indicators", views.EconomicIndicatorViewSet)
router.register(r"news", views.NewsArticleViewSet)
router.register(r"events", views.EconomicEventViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("prices/<str:pair>/", views.prices_view, name="prices"),
    path("calendar/", economic_calendar, name="economic-calendar"),
    path("technicals/<str:pair>/", technical_indicators, name="technical-indicators"),
]
