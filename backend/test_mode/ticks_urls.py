from django.urls import path

from .views import TicksView

urlpatterns = [
    path("ticks", TicksView.as_view(), name="ticks"),
]

