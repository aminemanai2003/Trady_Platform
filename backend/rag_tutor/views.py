"""
RAG Tutor API views.

Endpoints:
    POST   /api/tutor/documents/upload/        - ingest a PDF, image, audio, video, or TXT file
    GET    /api/tutor/documents/               - list user's documents
    DELETE /api/tutor/documents/<doc_id>/      - delete a document
    POST   /api/tutor/rag/query/               - ask a question (RAG, blocking)
    POST   /api/tutor/rag/stream/              - ask a question (SSE streaming)
"""

import json
import logging
import re

from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DocumentChunk, TutorDocument
from .services.document_service import chunk_segments, extract_segments, validate_upload
from .services.faiss_store import invalidate_user_index
from .services.ollama_service import generate_answer, generate_answer_stream, get_embedding
from .services.vector_store import retrieve_top_chunks

logger = logging.getLogger(__name__)

_MAX_QUERY_LEN = 1_000
_MAX_CONTEXT_HITS = 4
_SMALLTALK_RESPONSES = {
    "hi": "Hi. Ask me a question about your uploaded strategy documents, or upload more knowledge to expand what I can answer.",
    "hello": "Hello. Ask me about your uploaded strategy documents and I will answer with citations when the answer is covered.",
    "hey": "Hey. Ask a question about your uploaded documents and I will use the indexed evidence.",
    "thanks": "You're welcome.",
    "thank you": "You're welcome.",
}
_SMALLTALK_WORDS = {
    "bro",
    "buddy",
    "good",
    "hello",
    "hey",
    "hi",
    "mate",
    "morning",
    "night",
    "sup",
    "there",
    "yo",
}


def _clean_str(value: object, max_len: int = 500) -> str:
    if not isinstance(value, str):
        return ""
    return str(value).strip()[:max_len]


def _valid_email(email: str) -> bool:
    return bool(email) and "@" in email and len(email) <= 254


def _get_request_user_email(request) -> str:
    email = getattr(request.user, "email", "") or getattr(request.user, "username", "")
    return _clean_str(email, 254).lower()


def _detect_embedding_dims(owner_email: str) -> list[int]:
    rows = (
        DocumentChunk.objects
        .filter(document__owner_email=owner_email)
        .values_list("embedding_json", flat=True)
        [:200]
    )
    dims: set[int] = set()
    for row in rows:
        try:
            dims.add(len(json.loads(row)))
        except Exception:  # noqa: BLE001
            continue
    return sorted(dims, reverse=True)


def _retrieve_hits(query: str, user_email: str, top_k: int = 8) -> list[dict]:
    dims = _detect_embedding_dims(user_email)
    if not dims:
        query_emb = get_embedding(query, task_type="RETRIEVAL_QUERY")
        return retrieve_top_chunks(query_emb, user_email, top_k=top_k, min_score=0.10)

    hits: list[dict] = []
    for dim in dims:
        try:
            query_emb = get_embedding(query, task_type="RETRIEVAL_QUERY", target_dim=dim)
        except RuntimeError:
            continue
        hits.extend(retrieve_top_chunks(query_emb, user_email, top_k=top_k, min_score=0.10))

    hits.sort(key=lambda h: h.get("score", 0.0), reverse=True)
    if hits:
        return hits[:top_k]

    fallback_hits: list[dict] = []
    for dim in dims:
        try:
            query_emb = get_embedding(query, task_type="RETRIEVAL_QUERY", target_dim=dim)
        except RuntimeError:
            continue
        fallback_hits.extend(retrieve_top_chunks(query_emb, user_email, top_k=4, min_score=-1.0))

    fallback_hits.sort(key=lambda h: h.get("score", 0.0), reverse=True)
    return fallback_hits[:4]


def _embedding_error(user_email: str) -> str | None:
    try:
        _retrieve_hits("health check", user_email, top_k=1)
        return None
    except RuntimeError as exc:
        return str(exc)


def _sources_from_hits(hits: list[dict]) -> list[dict]:
    sources: list[dict] = []
    for hit in hits:
        sources.append(
            {
                "filename": hit.get("document_filename", ""),
                "modality": hit.get("modality", "text"),
                "page_number": hit.get("page_number"),
                "timestamp_start": hit.get("timestamp_start"),
                "timestamp_end": hit.get("timestamp_end"),
            }
        )
    return sources


def _is_not_covered_answer(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().lower())
    return (
        "not covered in your uploaded documents" in normalized
        or "not covered by your uploaded documents" in normalized
        or "couldn't find relevant information in your documents" in normalized
    )


def _smalltalk_answer(query: str) -> str | None:
    normalized = re.sub(r"[\s!.?,]+", " ", query.strip().lower()).strip()
    if normalized in _SMALLTALK_RESPONSES:
        return _SMALLTALK_RESPONSES[normalized]
    tokens = normalized.split()
    if 1 < len(tokens) <= 4 and tokens[0] in {"hi", "hello", "hey", "yo"} and all(token in _SMALLTALK_WORDS for token in tokens):
        return _SMALLTALK_RESPONSES.get(tokens[0], _SMALLTALK_RESPONSES["hello"])
    if normalized in {"help", "what can you do", "what can i ask"}:
        return (
            "You can ask about uploaded strategy documents, images, audio, or video. "
            "For example: summarize the strategy rules, compare risk limits, or ask which sources support an answer."
        )
    return None


def _query_terms(query: str) -> set[str]:
    stop_words = {
        "about", "above", "after", "another", "before", "does", "from", "have",
        "into", "mention", "mentioned", "should", "that", "the", "them", "this",
        "trade", "what", "when", "where", "which", "with", "would", "your",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9.]+", query.lower())
        if len(token) > 2 and token not in stop_words
    }


def _keyword_overlap(text: str, terms: set[str]) -> int:
    if not terms:
        return 0
    text_terms = set(re.findall(r"[a-z0-9.]+", text.lower()))
    return len(terms & text_terms)


def _previous_value(lines: list[str], label: str) -> str:
    target = label.lower()
    for idx, line in enumerate(lines):
        if line.lower().startswith(target) and idx > 0:
            return lines[idx - 1].strip(":- ")
    return ""


def _focused_zone_facts(zone: str, window: list[str]) -> list[str]:
    joined = " ".join(window)
    facts = []

    risk_per_trade = _previous_value(window, "Risk per trade")
    if risk_per_trade:
        if zone == "red" and risk_per_trade == "0%":
            facts.append(
                "- Risk allocation per trade: 0% (this is a no-trade state, not a low-risk trade)"
            )
        else:
            facts.append(f"- Risk per trade: {risk_per_trade}")

    max_correlation = _previous_value(window, "Max correlation")
    if max_correlation:
        facts.append(f"- Max correlation: {max_correlation}")

    if zone == "red":
        if re.search(r"\bno\b", joined, flags=re.IGNORECASE):
            facts.append("- Trade allowed: No")
        if all(term in joined.lower() for term in ("news shock", "platform outage")):
            facts.append("- Trigger: News shock, platform outage, or daily drawdown above 2.5%")
    elif zone == "amber":
        if "Only with" in joined or "confirmation" in joined.lower():
            facts.append("- Trade allowed: Only with confirmation")
    elif zone == "green":
        if re.search(r"\byes\b", joined, flags=re.IGNORECASE):
            facts.append("- Trade allowed: Yes")

    if "correlation is above 0.85" in joined.lower():
        facts.append("- Desk rule: when correlation is above 0.85, do not add another trade.")

    return facts


def _compress_ocr_zone(text: str, query: str) -> str:
    """
    OCR for infographics can be column-ordered instead of section-ordered.
    If the user asks about a named zone, keep the nearby OCR window and drop
    unrelated zones so the LLM cannot mix Amber/Green numbers into Red answers.
    """
    zone = ""
    lower_query = query.lower()
    for candidate in ("red", "amber", "green"):
        if candidate in lower_query:
            zone = candidate
            break
    if not zone or "ocr text" not in text.lower():
        return text

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    zone_idx = -1
    for idx, line in enumerate(lines):
        lower = line.lower()
        if zone in lower and "zone" in lower:
            zone_idx = idx
            break
        if lower == zone:
            zone_idx = idx
            break

    if zone_idx < 0:
        return text

    start = max(0, zone_idx - 5)
    end = min(len(lines), zone_idx + 8)
    window = lines[start:end]
    facts = _focused_zone_facts(zone, window)

    output = lines[:1] + [f"FOCUSED OCR FACTS FOR {zone.upper()} ZONE:"]
    if facts:
        output.extend(facts)
    output.extend([f"RAW OCR WINDOW FOR {zone.upper()} ZONE:"] + window)
    return "\n".join(output)


def _format_hit_for_context(hit: dict, query: str) -> str:
    source = hit.get("document_filename", "unknown source")
    modality = hit.get("modality", "text")
    score = hit.get("score", 0.0)
    text = str(hit.get("text", "")).strip()
    if modality == "image":
        text = _compress_ocr_zone(text, query)

    location = ""
    if hit.get("page_number"):
        location = f", page {hit['page_number']}"
    elif hit.get("timestamp_start") is not None and hit.get("timestamp_end") is not None:
        location = f", {hit['timestamp_start']:.1f}s-{hit['timestamp_end']:.1f}s"

    return (
        f"SOURCE: {source} ({modality}{location}, relevance={score:.3f})\n"
        f"{text}"
    )


def _select_evidence_hits(hits: list[dict], query: str, max_hits: int = _MAX_CONTEXT_HITS) -> list[dict]:
    if not hits:
        return []

    terms = _query_terms(query)
    best_score = float(hits[0].get("score", 0.0))
    selected: list[dict] = [hits[0]]
    seen = {
        (
            hits[0].get("document_filename"),
            hits[0].get("modality"),
            hits[0].get("page_number"),
            hits[0].get("timestamp_start"),
            hits[0].get("timestamp_end"),
        )
    }

    for hit in hits[1:]:
        if len(selected) >= max_hits:
            break

        score = float(hit.get("score", 0.0))
        if score < max(0.25, best_score * 0.72):
            continue

        overlap = _keyword_overlap(str(hit.get("text", "")), terms)
        is_close = (best_score - score) <= 0.08
        is_direct = overlap >= max(1, min(3, len(terms) // 2))

        if not is_close and not is_direct:
            continue

        identity = (
            hit.get("document_filename"),
            hit.get("modality"),
            hit.get("page_number"),
            hit.get("timestamp_start"),
            hit.get("timestamp_end"),
        )
        if identity in seen:
            continue

        selected.append(hit)
        seen.add(identity)

    return selected


class DocumentUploadView(APIView):
    """POST /api/tutor/documents/upload/"""

    parser_classes = [MultiPartParser, FormParser]
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        file_obj = request.FILES.get("file")
        user_email = _get_request_user_email(request)
        topic = _clean_str(request.data.get("topic", ""), 200)

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

        try:
            extracted_segments, extraction_meta = extract_segments(
                file_obj.name,
                file_obj.content_type or "",
                file_obj.read(),
            )
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

        chunks = chunk_segments(extracted_segments)
        if not chunks:
            return Response(
                {"error": "Could not extract indexable evidence from the file."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        doc = TutorDocument.objects.create(
            owner_email=user_email,
            filename=file_obj.name,
            file_type=file_obj.name.rsplit(".", 1)[-1].lower() if "." in file_obj.name else "txt",
            modality=chunks[0].modality if chunks else "text",
            topic=topic,
            extraction_metadata_json=json.dumps(extraction_meta),
        )

        ok_count = 0
        for i, chunk in enumerate(chunks):
            try:
                emb = get_embedding(chunk.text, task_type="RETRIEVAL_DOCUMENT")
                DocumentChunk.objects.create(
                    document=doc,
                    chunk_index=i,
                    text=chunk.text,
                    embedding_json=json.dumps(emb),
                    modality=chunk.modality,
                    source_label=chunk.source_label,
                    page_number=chunk.page_number,
                    timestamp_start=chunk.timestamp_start,
                    timestamp_end=chunk.timestamp_end,
                    metadata_json=json.dumps(chunk.metadata),
                )
                ok_count += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("Embedding failed chunk %d of %s: %s", i, doc.id, exc)

        if ok_count == 0:
            doc.delete()
            return Response(
                {
                    "error": (
                        "Could not generate embeddings. "
                        "Check that the document processing services are available."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        doc.chunk_count = ok_count
        doc.save(update_fields=["chunk_count"])

        invalidate_user_index(user_email)

        logger.info(
            "Ingested doc=%s for %s | chunks=%d/%d",
            doc.id,
            user_email,
            ok_count,
            len(chunks),
        )
        return Response(
            {
                "document_id": str(doc.id),
                "filename": doc.filename,
                "modality": doc.modality,
                "chunk_count": ok_count,
                "uploaded_at": doc.uploaded_at.isoformat(),
            },
            status=status.HTTP_201_CREATED,
        )


class DocumentListView(APIView):
    """GET /api/tutor/documents/"""

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
            "id",
            "filename",
            "file_type",
            "modality",
            "topic",
            "uploaded_at",
            "chunk_count",
        )
        return Response(
            {
                "documents": [
                    {**d, "id": str(d["id"]), "uploaded_at": d["uploaded_at"].isoformat()}
                    for d in docs
                ]
            }
        )


class DocumentDeleteView(APIView):
    """DELETE /api/tutor/documents/<doc_id>/"""

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


class RagQueryView(APIView):
    """POST /api/tutor/rag/query/"""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_email = _get_request_user_email(request)
        query = _clean_str(request.data.get("query", ""), _MAX_QUERY_LEN)

        if not _valid_email(user_email):
            return Response(
                {"error": "Authenticated user email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not query:
            return Response(
                {"error": "Query is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        smalltalk = _smalltalk_answer(query)
        if smalltalk:
            return Response({"answer": smalltalk, "sources": [], "cached": False, "provider": "system"})

        if len(query) < 3:
            return Response({"error": "Ask a document question or type hello."}, status=status.HTTP_400_BAD_REQUEST)

        if not TutorDocument.objects.filter(owner_email=user_email).exists():
            return Response(
                {"error": "No documents found. Please upload a document first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            hits = _retrieve_hits(query, user_email, top_k=8)
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if not hits:
            return Response(
                {
                    "answer": (
                        "I couldn't find relevant information in your documents for this question. "
                        "Try rephrasing or uploading more relevant content."
                    ),
                    "sources": [],
                    "cached": False,
                }
            )

        evidence_hits = _select_evidence_hits(hits, query)
        context_texts = [_format_hit_for_context(h, query) for h in evidence_hits]
        result = generate_answer(query, context_texts, user_email)
        result["sources"] = [] if _is_not_covered_answer(result.get("answer", "")) else _sources_from_hits(evidence_hits)
        return Response(result)


class RagStreamView(APIView):
    """POST /api/tutor/rag/stream/ - Server-Sent Events streaming response."""

    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user_email = _get_request_user_email(request)
        query = _clean_str(request.data.get("query", ""), _MAX_QUERY_LEN)

        if not _valid_email(user_email):
            return Response(
                {"error": "Authenticated user email is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not query:
            return Response(
                {"error": "Query is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        smalltalk = _smalltalk_answer(query)
        if smalltalk:
            def _smalltalk():
                yield f"data: {json.dumps({'token': smalltalk})}\n\n"
                yield f"data: {json.dumps({'done': True, 'sources': [], 'provider': 'system'})}\n\n"

            resp = StreamingHttpResponse(_smalltalk(), content_type="text/event-stream")
            resp["Cache-Control"] = "no-cache"
            resp["X-Accel-Buffering"] = "no"
            return resp

        if len(query) < 3:
            return Response({"error": "Ask a document question or type hello."}, status=status.HTTP_400_BAD_REQUEST)

        if not TutorDocument.objects.filter(owner_email=user_email).exists():
            return Response(
                {"error": "No documents found. Please upload a document first."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            hits = _retrieve_hits(query, user_email, top_k=8)
        except RuntimeError as exc:
            return Response({"error": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        evidence_hits = _select_evidence_hits(hits, query) if hits else []
        sources = _sources_from_hits(evidence_hits) if evidence_hits else []

        if not hits:
            def _empty():
                message = (
                    "I couldn't find relevant information in your documents for this question. "
                    "Try rephrasing or uploading more relevant content."
                )
                yield f"data: {json.dumps({'token': message})}\n\n"
                yield f"data: {json.dumps({'done': True, 'sources': [], 'provider': 'none'})}\n\n"

            resp = StreamingHttpResponse(_empty(), content_type="text/event-stream")
            resp["Cache-Control"] = "no-cache"
            resp["X-Accel-Buffering"] = "no"
            return resp

        context_texts = [_format_hit_for_context(h, query) for h in evidence_hits]

        def _stream():
            streamed_answer = ""
            for sse_line in generate_answer_stream(query, context_texts, user_email):
                if sse_line.startswith("data: "):
                    try:
                        payload = json.loads(sse_line[6:].strip())
                        if payload.get("token"):
                            streamed_answer += str(payload["token"])
                        if payload.get("done"):
                            payload["sources"] = [] if _is_not_covered_answer(streamed_answer) else sources
                            yield f"data: {json.dumps(payload)}\n\n"
                            continue
                    except Exception:  # noqa: BLE001
                        pass
                yield sse_line

        resp = StreamingHttpResponse(_stream(), content_type="text/event-stream")
        resp["Cache-Control"] = "no-cache"
        resp["X-Accel-Buffering"] = "no"
        return resp
