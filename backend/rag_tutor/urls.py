from django.urls import path

from .views import DocumentDeleteView, DocumentListView, DocumentUploadView, RagQueryView

urlpatterns = [
    path("documents/upload/",        DocumentUploadView.as_view(), name="tutor-upload"),
    path("documents/",               DocumentListView.as_view(),   name="tutor-docs"),
    path("documents/<str:doc_id>/",  DocumentDeleteView.as_view(), name="tutor-doc-delete"),
    path("rag/query/",               RagQueryView.as_view(),       name="tutor-query"),
]
