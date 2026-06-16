from django.urls import path
from . import views

urlpatterns = [
    path("positions/", views.PositionsView.as_view(), name="paper-positions"),
    path("positions/<int:pk>/", views.PositionDetailView.as_view(), name="paper-position-detail"),
    path("history/", views.TradeHistoryView.as_view(), name="paper-history"),
    path("stats/", views.PortfolioStatsView.as_view(), name="paper-stats"),
]
