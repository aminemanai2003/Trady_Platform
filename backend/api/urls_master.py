"""URL routing for the master signal endpoint."""
from django.urls import path
from .views_master import MasterSignalView

urlpatterns = [
    path("v2/master/generate/", MasterSignalView.as_view(), name="master-generate"),
]
