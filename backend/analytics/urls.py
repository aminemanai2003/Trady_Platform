from django.urls import path
from . import views

urlpatterns = [
    path("kpis/", views.kpis_view, name="kpis"),
    path("analytics/performance/", views.performance_view, name="performance"),
]
