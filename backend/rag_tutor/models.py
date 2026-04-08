import uuid

from django.db import models


class TutorDocument(models.Model):
    """
    A document uploaded by a user for RAG-based learning.
    Identified by owner_email (not FK to User so it works without Django login).
    """
    id          = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner_email = models.EmailField(db_index=True)
    filename    = models.CharField(max_length=255)
    file_type   = models.CharField(max_length=10)   # 'pdf' or 'txt'
    topic       = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    chunk_count = models.IntegerField(default=0)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"{self.filename} ({self.owner_email})"


class DocumentChunk(models.Model):
    """
    A text chunk with its Gemini embedding stored as JSON.
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document      = models.ForeignKey(TutorDocument, on_delete=models.CASCADE, related_name="chunks")
    chunk_index   = models.IntegerField()
    text          = models.TextField()
    embedding_json = models.TextField()  # JSON-serialized list[float] — 768 dims

    class Meta:
        ordering = ["chunk_index"]
        unique_together = [("document", "chunk_index")]

    def __str__(self) -> str:
        return f"Chunk {self.chunk_index} of {self.document.filename}"
