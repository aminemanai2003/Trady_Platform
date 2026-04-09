"""
Document ingestion service — PDF/TXT parsing + text chunking.

Supports:
  - PDF via pypdf  (text-layer PDFs)
  - Plain text files (UTF-8 / latin-1)

Chunking strategy:
  - Target ~500 chars per chunk (~350 tokens)
  - Hard cap at 900 chars
  - 100-char overlap to preserve context across chunk boundaries
  - Split on sentence boundaries when possible
"""

import io
import logging
import re

logger = logging.getLogger(__name__)

_CHUNK_TARGET  = 600    # target chars (~430 tokens — fits nomic-embed-text 2048 limit)
_CHUNK_MAX     = 1000   # hard cap
_CHUNK_OVERLAP = 100    # overlap chars
_MIN_CHUNK_LEN = 60     # discard very short chunks

_MAX_FILE_BYTES   = 10 * 1024 * 1024   # 10 MB
_ALLOWED_EXTS     = {".pdf", ".txt"}


# ── Validation ────────────────────────────────────────────────────────────────

def validate_upload(filename: str, content_type: str, size: int) -> dict:
    """Returns {"ok": True} or {"ok": False, "error": str}."""
    ext = ""
    if "." in filename:
        ext = "." + filename.rsplit(".", 1)[-1].lower()

    if ext not in _ALLOWED_EXTS:
        return {"ok": False, "error": "Only PDF and TXT files are supported."}
    if size <= 0:
        return {"ok": False, "error": "File is empty."}
    if size > _MAX_FILE_BYTES:
        return {"ok": False, "error": "File too large. Maximum is 10 MB."}
    return {"ok": True}


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
