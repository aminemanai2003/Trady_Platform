from django.urls import path
from . import views

urlpatterns = [
    path("kpis/", views.kpis_view, name="kpis"),
    path("analytics/performance/", views.performance_view, name="performance"),
    path("analytics/reports/summary/", views.reports_summary_view, name="reports-summary"),
    path("analytics/reports/export/", views.reports_export_csv_view, name="reports-export"),
    path("reports/summary/", views.reports_summary_view, name="signal-reports-summary"),
    path("reports/export/", views.reports_export_csv_view, name="signal-reports-export"),
]
