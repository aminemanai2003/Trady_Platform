from django.urls import path

from .views import (
    TestingTradesView,
    TestingCloseTradeView,
    TestingSummaryView,
    TestingResetView,
    TestingCoachView,
)

urlpatterns = [
    path("trades", TestingTradesView.as_view(), name="testing-trades"),
    path("trades/<str:trade_id>/close", TestingCloseTradeView.as_view(), name="testing-close-trade"),
    path("summary", TestingSummaryView.as_view(), name="testing-summary"),
    path("reset", TestingResetView.as_view(), name="testing-reset"),
    path("coach", TestingCoachView.as_view(), name="testing-coach"),
]

