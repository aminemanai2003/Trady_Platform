"""
RAG Tutor API views.

Endpoints:
    POST   /api/tutor/documents/upload/        — ingest a PDF or TXT file
    GET    /api/tutor/documents/               — list user's documents
    DELETE /api/tutor/documents/<doc_id>/      — delete a document
    POST   /api/tutor/rag/query/               — ask a question (RAG, blocking)
    POST   /api/tutor/rag/stream/              — ask a question (SSE streaming)
"""

import json
import logging

from django.http import StreamingHttpResponse
from rest_framework.authentication import TokenAuthentication
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DocumentChunk, TutorDocument
from .services.document_service import chunk_text, extract_text, validate_upload
from .services.faiss_store import invalidate_user_index
from .services.ollama_service import generate_answer, generate_answer_stream, get_embedding
from .services.vector_store import retrieve_top_chunks

logger = logging.getLogger(__name__)

_MAX_QUERY_LEN = 1_000


def _clean_str(value: object, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return str(value).strip()[:max_len]


def _valid_email(email: str) -> bool:
    return bool(email) and "@" in email and len(email) <= 254


def _get_request_user_email(request) -> str:
    email = getattr(request.user, "email", "") or getattr(request.user, "username", "")
    return _clean_str(email, 254).lower()


def _detect_embedding_dim(owner_email: str) -> int | None:
    """Return the vector dimension used for this user's stored chunks, or None."""
    row = (
        DocumentChunk.objects
        .filter(document__owner_email=owner_email)
        .values_list("embedding_json", flat=True)
        .first()
    )
    if not row:
        return None
    try:
        return len(json.loads(row))
    except Exception:  # noqa: BLE001
        return None


# ── Upload ────────────────────────────────────────────────────────────────────

class DocumentUploadView(APIView):
    """POST /api/tutor/documents/upload/"""

    parser_classes     = [MultiPartParser, FormParser]
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_obj   = request.FILES.get("file")
        user_email = _get_request_user_email(request)
        topic      = _clean_str(request.data.get("topic", ""), 200)

        if not file_obj:
            return Response({"error": "No file provided."}, status=status.HTTP_400_BAD_REQUEST)

        if not _valid_email(user_email):
            return Response(
                {"error": "A valid user_email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        v = validate_upload(file_obj.name, file_obj.content_type or "", file_obj.size)
        if not v["ok"]:
            return Response({"error": v["error"]}, status=status.HTTP_400_BAD_REQUEST)

        # ── Extract text ──────────────────────────────────────────────────────
        try:
            raw_text = extract_text(file_obj.name, file_obj.read())
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        if not raw_text.strip():
            return Response(
                {"error": "No text could be extracted from the document."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Chunk ─────────────────────────────────────────────────────────────
        chunks = chunk_text(raw_text)
        if not chunks:
            return Response(
                {"error": "Could not split document into chunks."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Persist document record ───────────────────────────────────────────
        doc = TutorDocument.objects.create(
            owner_email = user_email,
            filename    = file_obj.name,
            file_type   = "pdf" if file_obj.name.lower().endswith(".pdf") else "txt",
            topic       = topic,
        )

        # ── Embed + store chunks ──────────────────────────────────────────────
        ok_count = 0
        for i, chunk_str in enumerate(chunks):
            try:
                emb = get_embedding(chunk_str, task_type="RETRIEVAL_DOCUMENT")
                DocumentChunk.objects.create(
                    document       = doc,
                    chunk_index    = i,
                    text           = chunk_str,
                    embedding_json = json.dumps(emb),
                )
                ok_count += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("Embedding failed chunk %d of %s: %s", i, doc.id, exc)

        # Abort if nothing was embedded
        if ok_count == 0:
            doc.delete()
            return Response(
                {
                    "error": (
                        "Could not generate embeddings. "
                        "Check that GEMINI_API_KEY is set and valid."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        doc.chunk_count = ok_count
        doc.save(update_fields=["chunk_count"])

        # Rebuild Faiss index for this user on next query
        invalidate_user_index(user_email)

        logger.info(
            "Ingested doc=%s for %s | chunks=%d/%d",
            doc.id, user_email, ok_count, len(chunks),
        )
        return Response(
            {
                "document_id": str(doc.id),
                "filename":    doc.filename,
                "chunk_count": ok_count,
                "uploaded_at": doc.uploaded_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


# ── List / Delete ─────────────────────────────────────────────────────────────

class DocumentListView(APIView):
    """GET /api/tutor/documents/?user_email=..."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_email = _get_request_user_email(request)
        if not _valid_email(user_email):
            return Response(
                {"error": "Authenticated user email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        docs = TutorDocument.objects.filter(owner_email=user_email).values(
            "id", "filename", "file_type", "topic", "uploaded_at", "chunk_count"
        )
        return Response({
            "documents": [
                {**d, "id": str(d["id"]), "uploaded_at": d["uploaded_at"].isoformat()}
                for d in docs
            ]
        })


class DocumentDeleteView(APIView):
    """DELETE /api/tutor/documents/<doc_id>/?user_email=..."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def delete(self, request, doc_id: str):
        user_email = _get_request_user_email(request)
        if not _valid_email(user_email):
            return Response(
                {"error": "Authenticated user email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            doc = TutorDocument.objects.get(id=doc_id, owner_email=user_email)
        except TutorDocument.DoesNotExist:
            return Response({"error": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        doc.delete()
        invalidate_user_index(user_email)
        logger.info("Deleted doc=%s for %s", doc_id, user_email)
        return Response({"deleted": True})


# ── RAG Query ─────────────────────────────────────────────────────────────────

class RagQueryView(APIView):
    """POST /api/tutor/rag/query/"""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_email = _get_request_user_email(request)
        query      = _clean_str(request.data.get("query", ""), _MAX_QUERY_LEN)

        if not _valid_email(user_email):
            return Response(
                {"error": "Authenticated user email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not query or len(query) < 3:
            return Response(
                {"error": "Query must be at least 3 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not TutorDocument.objects.filter(owner_email=user_email).exists():
            return Response(
                {"error": "No documents found. Please upload a trading document first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # ── Embed query ───────────────────────────────────────────────────────
        # Detect stored embedding dim to select the matching model and avoid
        # cross-model (768↔384) cache hits that silently return zero results.
        stored_dim = _detect_embedding_dim(user_email)
        try:
            query_emb = get_embedding(query, task_type="RETRIEVAL_QUERY", target_dim=stored_dim)
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # ── Retrieve top chunks (strictly by user) ────────────────────────────
        hits = retrieve_top_chunks(query_emb, user_email, top_k=5, min_score=0.10)

        # Best-effort fallback: if no chunks reach the threshold, return the
        # top-3 regardless of score so the user always gets an answer when
        # documents exist (handles meta-queries like "what does this file cover").
        if not hits:
            hits = retrieve_top_chunks(query_emb, user_email, top_k=3, min_score=-1.0)

        if not hits:
            return Response({
                "answer": (
                    "I couldn't find relevant information in your documents for this question. "
                    "Try rephrasing or uploading more relevant content."
                ),
                "sources": [],
                "cached":  False,
            })

        context_texts = [h["text"] for h in hits]
        sources       = sorted({h["document_filename"] for h in hits})

        # ── Generate answer ───────────────────────────────────────────────────
        result = generate_answer(query, context_texts, user_email)
        result["sources"] = sources
        return Response(result)


# ── RAG Streaming Query ───────────────────────────────────────────────────────

class RagStreamView(APIView):
    """POST /api/tutor/rag/stream/ — Server-Sent Events streaming response."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_email = _get_request_user_email(request)
        query      = _clean_str(request.data.get("query", ""), _MAX_QUERY_LEN)

        if not _valid_email(user_email):
            return Response(
                {"error": "Authenticated user email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not query or len(query) < 3:
            return Response(
                {"error": "Query must be at least 3 characters."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not TutorDocument.objects.filter(owner_email=user_email).exists():
            return Response(
                {"error": "No documents found. Please upload a trading document first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        stored_dim = _detect_embedding_dim(user_email)
        try:
            query_emb = get_embedding(query, task_type="RETRIEVAL_QUERY", target_dim=stored_dim)
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        hits    = retrieve_top_chunks(query_emb, user_email, top_k=5, min_score=0.10)

        # Best-effort fallback (same logic as RagQueryView above)
        if not hits:
            hits = retrieve_top_chunks(query_emb, user_email, top_k=3, min_score=-1.0)

        sources = sorted({h["document_filename"] for h in hits}) if hits else []

        if not hits:
            def _empty():
                no_info = (
                    "I couldn't find relevant information in your documents for this question. "
                    "Try rephrasing or uploading more relevant content."
                )
                yield f"data: {json.dumps({'token': no_info})}\n\n"
                yield f"data: {json.dumps({'done': True, 'sources': [], 'provider': 'none'})}\n\n"

            resp = StreamingHttpResponse(_empty(), content_type="text/event-stream")
            resp["Cache-Control"] = "no-cache"
            resp["X-Accel-Buffering"] = "no"
            return resp

        context_texts = [h["text"] for h in hits]

        def _stream():
            for sse_line in generate_answer_stream(query, context_texts, user_email):
                if sse_line.startswith("data: "):
                    try:
                        payload = json.loads(sse_line[6:].strip())
                        if payload.get("done"):
                            payload["sources"] = sources
                            yield f"data: {json.dumps(payload)}\n\n"
                            continue
                    except Exception:  # noqa: BLE001
                        pass
                yield sse_line

        resp = StreamingHttpResponse(_stream(), content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp
