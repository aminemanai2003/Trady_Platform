"""
Django view for the OCR extraction endpoint.

POST /api/ocr/extract/
  Body  : multipart/form-data  — field name: "image"
  Returns: JSON  (see pipeline.run_pipeline for output schema)
"""

import logging

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

logger = logging.getLogger(__name__)

ALLOWED_CONTENT_TYPES = {
    "image/jpeg", "image/png", "image/jpg", "image/webp",
    "image/heic", "image/heif",           # Apple HEIC (iPhone)
    "image/heic-sequence", "image/heif-sequence",
    "application/octet-stream",           # generic binary fallback some clients send
}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB (HEIC files can be larger)


@csrf_exempt
@require_POST
def extract(request):
    """
    POST /api/ocr/extract/

    Accepts an image file under the form-field name ``image``.
    Returns structured identity fields as JSON.
    """
    uploaded = request.FILES.get("image")
    if uploaded is None:
        return JsonResponse(
            {"error": "No image provided. Send a file under the field name 'image'."},
            status=400,
        )

    # Resolve content type: browsers sometimes send 'application/octet-stream'
    # for HEIC files; fall back to extension-based detection.
    ct = uploaded.content_type or ""
    if ct not in ALLOWED_CONTENT_TYPES:
        ext = (uploaded.name or "").rsplit(".", 1)[-1].lower()
        ext_map = {"heic": "image/heic", "heif": "image/heif",
                   "jpg": "image/jpeg", "jpeg": "image/jpeg",
                   "png": "image/png", "webp": "image/webp"}
        ct = ext_map.get(ext, ct)
    if ct not in ALLOWED_CONTENT_TYPES:
        return JsonResponse(
            {"error": f"Unsupported type {ct!r}. Supported: JPEG, PNG, WebP, HEIC/HEIF."},
            status=400,
        )

    if uploaded.size > MAX_UPLOAD_BYTES:
        return JsonResponse({"error": "Image too large (max 10 MB)."}, status=400)

    try:
        image_bytes = uploaded.read()
        # Lazy import to keep server boot resilient when optional OCR deps
        # (opencv/easyocr, etc.) aren't installed on this machine.
        from .pipeline import run_pipeline

        result = run_pipeline(image_bytes)
        return JsonResponse(result)
    except Exception:
        logger.exception("Unhandled error in OCR extract view")
        return JsonResponse({"error": "Internal OCR processing error."}, status=500)
