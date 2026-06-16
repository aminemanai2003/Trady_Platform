"""
Image preprocessing module.

Steps:
  1. Decode image bytes → OpenCV array
  2. Attempt perspective correction (find document edges)
  3. Convert to grayscale
  4. Denoise (non-local means)
  5. Enhance contrast (CLAHE)

Returns a preprocessed grayscale numpy array ready for OCR.
"""

import logging

import cv2
import numpy as np

logger = logging.getLogger(__name__)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _bytes_to_cv(image_bytes: bytes) -> np.ndarray:
    """
    Decode raw image bytes to an OpenCV BGR array.
    Supports JPEG, PNG, WebP natively via OpenCV.
    Falls back to pillow-heif for HEIC/HEIF (iPhone photos).
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is not None:
        return img

    # HEIC/HEIF fallback — requires pillow-heif
    try:
        import pillow_heif
        from PIL import Image, ImageOps
        import io
        pillow_heif.register_heif_opener()
        pil_img = Image.open(io.BytesIO(image_bytes))
        # Apply EXIF orientation (iPhone photos are often rotated 90°)
        pil_img = ImageOps.exif_transpose(pil_img)
        pil_img = pil_img.convert("RGB")
        # PIL is RGB; OpenCV expects BGR
        bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        logger.info("Decoded HEIC/HEIF image via pillow-heif (%dx%d)", bgr.shape[1], bgr.shape[0])
        return bgr
    except Exception as exc:
        logger.debug("pillow-heif fallback failed: %s", exc)

    raise ValueError(
        "Could not decode image. Supported formats: JPEG, PNG, WebP, HEIC/HEIF."
    )


def _downscale_if_large(img: np.ndarray, max_long_edge: int = 3000) -> np.ndarray:
    """
    Downscale very large images (e.g. 4032px iPhone shots) to speed up OCR
    without losing text legibility.  max_long_edge=3000 keeps ~0.9 the detail
    while cutting OCR time by 30-40 %.
    """
    h, w = img.shape[:2]
    long_edge = max(h, w)
    if long_edge > max_long_edge:
        scale = max_long_edge / long_edge
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.debug("Downscaled from %dx%d to %dx%d", w, h, new_w, new_h)
    return img


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """Order four corner points as [top-left, top-right, bottom-right, bottom-left]."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    diff = np.diff(pts, axis=1)
    rect[0] = pts[np.argmin(s)]    # top-left  — smallest x+y
    rect[2] = pts[np.argmax(s)]    # bottom-right — largest x+y
    rect[1] = pts[np.argmin(diff)] # top-right
    rect[3] = pts[np.argmax(diff)] # bottom-left
    return rect


# ── Public steps ──────────────────────────────────────────────────────────────

def detect_and_correct_perspective(img: np.ndarray) -> np.ndarray:
    """
    Attempt document perspective correction.

    Looks for the largest quadrilateral contour (likely the document card)
    and applies a perspective warp to produce a frontal view.
    Returns the original image unchanged if no clear quadrilateral is found
    or if validity checks fail.

    Guards applied:
    - Quad area must be ≥15 % of image area
    - Warped output aspect ratio must be plausible for an ID card (0.4 – 2.5)
    """
    try:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, 75, 200)

        contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        doc_corners = None
        for contour in contours[:10]:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                doc_corners = approx
                break

        if doc_corners is None:
            return img

        corners = doc_corners.reshape(4, 2).astype(np.float32)

        # Guard 1: quad must be at least 15 % of the full image area
        img_area = img.shape[0] * img.shape[1]
        quad_area = cv2.contourArea(doc_corners)
        if quad_area < 0.15 * img_area:
            logger.debug("Perspective: quad too small (%.1f%% of image) — skipping", 100 * quad_area / img_area)
            return img

        rect = _order_corners(corners)
        tl, tr, br, bl = rect

        width  = int(max(np.linalg.norm(br - bl), np.linalg.norm(tr - tl)))
        height = int(max(np.linalg.norm(tr - br), np.linalg.norm(tl - bl)))

        if width < 100 or height < 60:
            return img

        # Guard 2: aspect ratio sanity (ID cards are roughly 1.58:1 or held portrait)
        aspect = width / height
        if not (0.4 <= aspect <= 2.6):
            logger.debug("Perspective: aspect ratio %.2f out of range — skipping", aspect)
            return img

        dst = np.array(
            [[0, 0], [width - 1, 0], [width - 1, height - 1], [0, height - 1]],
            dtype=np.float32,
        )
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(img, M, (width, height))

    except Exception as exc:
        logger.warning("Perspective correction failed (%s) — using original", exc)
        return img


def to_grayscale(img: np.ndarray) -> np.ndarray:
    """Convert BGR image to grayscale."""
    if len(img.shape) == 2:
        return img  # already grayscale
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def denoise(gray: np.ndarray, strength: int = 10) -> np.ndarray:
    """Remove noise using non-local means denoising."""
    return cv2.fastNlMeansDenoising(gray, h=strength, templateWindowSize=7, searchWindowSize=21)


def enhance_contrast(gray: np.ndarray, clip_limit: float = 2.0) -> np.ndarray:
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)."""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=(8, 8))
    return clahe.apply(gray)


def upscale_if_small(img: np.ndarray, min_width: int = 900) -> np.ndarray:
    """Upscale images narrower than min_width px (e.g. phone photos of cards)."""
    h, w = img.shape[:2]
    if w < min_width:
        scale = min_width / w
        new_w, new_h = int(w * scale), int(h * scale)
        img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        logger.debug("Upscaled image from %dx%d to %dx%d", w, h, new_w, new_h)
    return img


def preprocess(image_bytes: bytes) -> np.ndarray:
    """
    Full preprocessing pipeline.

    Adapts based on image type:
    - High-res images (≥1500 px wide, e.g. phone HEIC):
        * Gamma correction for dark photos (mean brightness < 110)
        * Perspective correction attempted on the brightened image
        * CLAHE without heavy NLM denoising
    - Low-res / compressed scans:
        * Perspective correction + standard NLM denoise + CLAHE

    Returns a high-contrast grayscale numpy array suitable for OCR.
    Raises ValueError if the image cannot be decoded.
    """
    img = _bytes_to_cv(image_bytes)
    img = _downscale_if_large(img)     # cap very large phone photos first
    img = upscale_if_small(img)        # upscale tiny/compressed scans

    h, w = img.shape[:2]
    hi_res = max(h, w) >= 1500

    gray = to_grayscale(img)

    if hi_res:
        # ── Step 1: brightness correction (gamma) ─────────────────────────
        mean_brightness = float(gray.mean())
        logger.debug("Hi-res image %dx%d, mean brightness=%.1f", w, h, mean_brightness)

        if mean_brightness < 110:
            # gamma < 1 brightens dark images; scale dynamically with darkness
            gamma = max(0.35, mean_brightness / 200.0)
            table = np.array(
                [min(255, int(((i / 255.0) ** gamma) * 255)) for i in range(256)],
                dtype=np.uint8,
            )
            gray = cv2.LUT(gray, table)
            logger.debug("Applied gamma=%.2f (brightness was %.1f)", gamma, mean_brightness)

        # ── Step 2: perspective correction using the brightened gray ──────
        # Build a temporary BGR from brightened gray just for warp detection
        img_bright = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        warped_bright = detect_and_correct_perspective(img_bright)
        if warped_bright is not img_bright:
            # Perspective correction succeeded — use the warped version
            gray = to_grayscale(warped_bright)
            logger.debug("Perspective correction applied on hi-res image")

        # ── Step 3: CLAHE only (skip NLM for hi-res — too slow/destructive) ─
        gray = enhance_contrast(gray, clip_limit=3.0)
    else:
        # Scanned / compressed images: full pipeline
        img  = detect_and_correct_perspective(img)
        gray = to_grayscale(img)
        gray = denoise(gray, strength=10)
        gray = enhance_contrast(gray, clip_limit=2.0)
    return gray
