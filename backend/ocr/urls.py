from django.urls import path

from . import views

app_name = "ocr"

urlpatterns = [
    path("extract/", views.extract, name="extract"),
]
