"""
PHASE 6: API URL Configuration
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.views import (
    SignalViewSet, AgentExplanationViewSet, BacktestViewSet,
    HealthViewSet, FeatureViewSet
)

router = DefaultRouter()
router.register(r'signals', SignalViewSet, basename='signals')
router.register(r'agent', AgentExplanationViewSet, basename='agent')
router.register(r'backtest', BacktestViewSet, basename='backtest')
router.register(r'health', HealthViewSet, basename='health')
router.register(r'features', FeatureViewSet, basename='features')

urlpatterns = [
    path('', include(router.urls)),
]
