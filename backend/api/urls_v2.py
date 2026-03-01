"""
URL configuration for V2 API
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_v2 import (
    TradingSignalV2ViewSet,
    PerformanceMonitoringViewSet,
    ExplainabilityViewSet,
    BacktestingViewSet,
    CorrelationViewSet,
    ValidationViewSet,
)

router = DefaultRouter()
router.register(r'signals', TradingSignalV2ViewSet, basename='signals-v2')
router.register(r'monitoring', PerformanceMonitoringViewSet, basename='monitoring-v2')
router.register(r'explain', ExplainabilityViewSet, basename='explain-v2')
router.register(r'backtesting', BacktestingViewSet, basename='backtesting-v2')
router.register(r'correlations', CorrelationViewSet, basename='correlations-v2')
router.register(r'validation', ValidationViewSet, basename='validation-v2')

urlpatterns = [
    path('v2/', include(router.urls)),
]
