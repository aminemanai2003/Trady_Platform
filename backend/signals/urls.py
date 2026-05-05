from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r"signals", views.TradingSignalViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path("signals/latest/", views.latest_signals, name="latest-signals"),
    path("signals/decision/<str:symbol>/", views.DecisionView.as_view(), name="signal-decision"),
]
