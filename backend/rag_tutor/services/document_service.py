"""
Document ingestion service — PDF/TXT parsing + text chunking.

Supports:
  - PDF via pypdf  (text-layer PDFs)
  - Plain text files (UTF-8 / latin-1)
  - Images via OCR / local vision model
  - Audio and video via local Whisper transcription

Chunking strategy:
  - Target ~500 chars per chunk (~350 tokens)
  - Hard cap at 900 chars
  - 100-char overlap to preserve context across chunk boundaries
  - Split on sentence boundaries when possible
"""

import io
import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_CHUNK_TARGET  = 600    # target chars (~430 tokens — fits nomic-embed-text 2048 limit)
_CHUNK_MAX     = 1000   # hard cap
_CHUNK_OVERLAP = 100    # overlap chars
_MIN_CHUNK_LEN = 60     # discard very short chunks

_MAX_FILE_BYTES = 250 * 1024 * 1024
_TEXT_MAX_BYTES = 10 * 1024 * 1024
_IMAGE_MAX_BYTES = 15 * 1024 * 1024
_AUDIO_MAX_BYTES = 50 * 1024 * 1024
_VIDEO_MAX_BYTES = 250 * 1024 * 1024

_TEXT_EXTS = {".pdf", ".txt", ".md"}
_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg"}
_VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
_ALLOWED_EXTS = _TEXT_EXTS | _IMAGE_EXTS | _AUDIO_EXTS | _VIDEO_EXTS


@dataclass
class ExtractedSegment:
    text: str
    modality: str
    source_label: str = ""
    page_number: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class EvidenceChunk:
    text: str
    modality: str
    source_label: str
    page_number: int | None = None
    timestamp_start: float | None = None
    timestamp_end: float | None = None
    metadata: dict = field(default_factory=dict)


# ── Validation ────────────────────────────────────────────────────────────────

def validate_upload(filename: str, content_type: str, size: int) -> dict:
    """Returns {"ok": True} or {"ok": False, "error": str}."""
    ext = get_extension(filename)

    if ext not in _ALLOWED_EXTS:
        return {"ok": False, "error": "Supported files: PDF, TXT, MD, images, audio, and video."}
    if size <= 0:
        return {"ok": False, "error": "File is empty."}
    if ext in _TEXT_EXTS and size > _TEXT_MAX_BYTES:
        return {"ok": False, "error": "Text/PDF file too large. Maximum is 10 MB."}
    if ext in _IMAGE_EXTS and size > _IMAGE_MAX_BYTES:
        return {"ok": False, "error": "Image file too large. Maximum is 15 MB."}
    if ext in _AUDIO_EXTS and size > _AUDIO_MAX_BYTES:
        return {"ok": False, "error": "Audio file too large. Maximum is 50 MB."}
    if ext in _VIDEO_EXTS and size > _VIDEO_MAX_BYTES:
        return {"ok": False, "error": "Video file too large. Maximum is 250 MB."}
    if size > _MAX_FILE_BYTES:
        return {"ok": False, "error": "File too large. Maximum is 250 MB."}
    return {"ok": True}


def get_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return "." + filename.rsplit(".", 1)[-1].lower()


def detect_modality(filename: str, content_type: str = "") -> str:
    ext = get_extension(filename)
    if ext in _IMAGE_EXTS or content_type.startswith("image/"):
        return "image"
    if ext in _AUDIO_EXTS or content_type.startswith("audio/"):
        return "audio"
    if ext in _VIDEO_EXTS or content_type.startswith("video/"):
        return "video"
    return "text"


# ── Text extraction ───────────────────────────────────────────────────────────

def _extract_pdf(file_bytes: bytes) -> str:
    try:
        import pypdf  # noqa: PLC0415  (optional dep)
    except ImportError as exc:
        raise RuntimeError(
            "PDF parsing requires `pypdf`. Run: pip install pypdf"
        ) from exc

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)
    except Exception as exc:  # noqa: BLE001
        logger.error("PDF parse error: %s", exc)
        raise RuntimeError(f"Could not parse PDF: {exc}") from exc


def _extract_pdf_segments(filename: str, file_bytes: bytes) -> list[ExtractedSegment]:
    try:
        import pypdf  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError(
            "PDF parsing requires `pypdf`. Run: pip install pypdf"
        ) from exc

    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        segments = []
        for idx, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if text.strip():
                segments.append(ExtractedSegment(
                    text=text,
                    modality="text",
                    source_label=filename,
                    page_number=idx,
                    metadata={"page_number": idx},
                ))
        return segments
    except Exception as exc:  # noqa: BLE001
        logger.error("PDF parse error: %s", exc)
        raise RuntimeError(f"Could not parse PDF: {exc}") from exc


def _extract_txt(file_bytes: bytes) -> str:
    try:
        return file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return file_bytes.decode("latin-1", errors="replace")


def extract_text(filename: str, file_bytes: bytes) -> str:
    """Route to the correct extractor based on filename extension."""
    if filename.lower().endswith(".pdf"):
        return _extract_pdf(file_bytes)
    return _extract_txt(file_bytes)


def extract_segments(filename: str, content_type: str, file_bytes: bytes) -> tuple[list[ExtractedSegment], dict]:
    """
    Extract text-grounded evidence segments from text, image, audio, or video.
    """
    modality = detect_modality(filename, content_type)
    ext = get_extension(filename)

    if modality == "image":
        from .image_service import extract_image_evidence  # noqa: PLC0415
        result = extract_image_evidence(filename, file_bytes)
        text = result["text"].strip()
        if not text:
            raise RuntimeError(
                "No text or visual description could be extracted from this image. "
                "Install a local Ollama vision model or upload a clearer image."
            )
        return [
            ExtractedSegment(
                text=text,
                modality="image",
                source_label=filename,
                metadata=result.get("metadata", {}),
            )
        ], result.get("metadata", {})

    if modality == "audio":
        from .audio_service import transcribe_audio  # noqa: PLC0415
        result = transcribe_audio(filename, file_bytes)
        raw_segments = result.get("segments", [])
        if not raw_segments:
            raise RuntimeError("No speech could be transcribed from this audio file.")
        segments = [
            ExtractedSegment(
                text=s["text"],
                modality="audio",
                source_label=filename,
                timestamp_start=s.get("start"),
                timestamp_end=s.get("end"),
                metadata={"timestamp_start": s.get("start"), "timestamp_end": s.get("end")},
            )
            for s in raw_segments
        ]
        return segments, result.get("metadata", {})

    if modality == "video":
        from .video_service import extract_video_evidence  # noqa: PLC0415
        result = extract_video_evidence(filename, file_bytes)
        raw_segments = result.get("segments", [])
        if not raw_segments:
            raise RuntimeError("No transcript or readable frame evidence could be extracted from this video file.")
        segments = [
            ExtractedSegment(
                text=s["text"],
                modality="video",
                source_label=filename,
                timestamp_start=s.get("start"),
                timestamp_end=s.get("end"),
                metadata=s.get("metadata", {}),
            )
            for s in raw_segments
            if str(s.get("text", "")).strip()
        ]
        return segments, result.get("metadata", {})

    if ext == ".pdf":
        segments = _extract_pdf_segments(filename, file_bytes)
        return segments, {"pages": len(segments)}

    text = _extract_txt(file_bytes)
    return [
        ExtractedSegment(
            text=text,
            modality="text",
            source_label=filename,
            metadata={"extension": ext or ".txt"},
        )
    ], {"extension": ext or ".txt"}


# ── Text cleaning ─────────────────────────────────────────────────────────────

def _clean(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)          # collapse blank lines
    text = re.sub(r"[ \t]+", " ", text)              # collapse whitespace
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text) # remove page-number-only lines
    return text.strip()


# ── Chunking ──────────────────────────────────────────────────────────────────

def chunk_text(text: str) -> list:
    """
    Split cleaned text into overlapping chunks.

    Returns list[str] where each string is 60–900 characters.
    """
    text = _clean(text)
    if not text:
        return []

    # Split on sentence-ending punctuation followed by whitespace
    sentences = re.split(r"(?<=[.!?])\s+|\n\n", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks: list = []
    current = ""

    for sentence in sentences:
        candidate = (current + " " + sentence).strip() if current else sentence

        if len(candidate) > _CHUNK_MAX and current:
            # Flush current chunk and start new with overlap
            chunks.append(current.strip())
            overlap_start = max(0, len(current) - _CHUNK_OVERLAP)
            current = current[overlap_start:].strip() + " " + sentence
        else:
            current = candidate

    if current.strip():
        chunks.append(current.strip())

    return [c for c in chunks if len(c) >= _MIN_CHUNK_LEN]


def chunk_segments(segments: list[ExtractedSegment]) -> list[EvidenceChunk]:
    """
    Split extracted segments into chunks while preserving source metadata.
    """
    evidence: list[EvidenceChunk] = []
    for segment in segments:
        chunks = chunk_text(segment.text)
        if not chunks and segment.text.strip():
            chunks = [segment.text.strip()]

        for chunk in chunks:
            if not chunk.strip():
                continue
            evidence.append(
                EvidenceChunk(
                    text=chunk,
                    modality=segment.modality,
                    source_label=segment.source_label,
                    page_number=segment.page_number,
                    timestamp_start=segment.timestamp_start,
                    timestamp_end=segment.timestamp_end,
                    metadata=segment.metadata,
                )
            )
    return evidence
