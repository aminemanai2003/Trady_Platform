"""
OCR Pipeline — main orchestration.

Steps
-----
1. Preprocess  : perspective correction → grayscale → denoise → contrast
2. OCR         : EasyOCR returns text + bounding boxes with confidence scores
3. Extraction  : spatial (label-neighbour) + inline regex pass
4. Validation  : normalise dates, score field completeness

Output format
-------------
{
  "first_name":    str,
  "last_name":     str,
  "date_of_birth": str,   # YYYY-MM-DD when recognised
  "nationality":   str,
  "id_number":     str,
  "confidence":    float,
  "issues":        dict,
  "raw_ocr_text":  str,
}
"""

import logging
from typing import Any, Dict

from .extractor import (
    extract_by_line_proximity,
    extract_fields_spatially,
    extract_inline_patterns,
    extract_names_heuristic,
    merge_extractions,
)
from .ocr_engine import run_ocr
from .preprocessor import preprocess
from .validator import validate_and_score

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _avg_confidence(ocr_results: list) -> float:
    if not ocr_results:
        return 0.0
    return round(sum(r["confidence"] for r in ocr_results) / len(ocr_results), 3)


def _join_text(ocr_results: list) -> str:
    """Concatenate OCR text in reading order (top-to-bottom, left-to-right).
    For Arabic/RTL cards the detections come right-to-left per row; we sort
    by Y first so rows are in natural reading order.
    """
    ordered = sorted(ocr_results, key=lambda r: (r["y_min"], r["x_min"]))
    return "\n".join(r["text"] for r in ordered)


def _stitch_arabic_date(raw_text: str, extracted: dict) -> None:
    """
    Post-process: if date_of_birth is a bare day/partial or missing, try to
    reconstruct it from nearby numbers/month names in the raw OCR text.

    Handles the common Tunisian CIN fragmentation:
        Line N:   تاريخ الولادة 07
        Line N+1: ماي 1994
    After label extraction we'd have date_of_birth = "07 ماي 1994" (combined)
    but if it still ends up partial, this function normalises it.
    """
    import re as _re
    from .validator import _NAMED_MONTHS, _DATE_NAMED_MONTH  # type: ignore

    dob = extracted.get("date_of_birth", "")

    # Already valid ISO or empty — nothing to stitch
    if not dob or _re.match(r"^\d{4}-\d{2}-\d{2}$", dob):
        return

    # Search the full raw text for a pattern like "07 ماي 1994" or "07 mai 1994"
    m = _DATE_NAMED_MONTH.search(raw_text)
    if m:
        day, month_name, year = m.group(1), m.group(2), m.group(3)
        month_num = _NAMED_MONTHS.get(month_name.lower()) or _NAMED_MONTHS.get(month_name)
        if month_num:
            extracted["date_of_birth"] = f"{year}-{month_num}-{day.zfill(2)}"
            return

    # Fallback: find standalone 4-digit year near a standalone 1-2 digit day
    year_m = _re.search(r"\b(19\d{2}|20\d{2})\b", raw_text)
    day_m  = _re.search(r"\b(\d{1,2})\b", dob)
    if year_m and day_m:
        # We can't know the month without month names — leave it for LLM fallback
        pass


def _split_full_name(extracted: Dict) -> Dict:
    """
    If first_name and last_name are both absent but full_name exists,
    split it naively: first token → first_name, rest → last_name.
    """
    if extracted.get("first_name") or extracted.get("last_name"):
        return extracted

    full = extracted.pop("full_name", None) or extracted.pop("fullName", None)
    if not full:
        return extracted

    parts = full.strip().split()
    extracted["first_name"] = parts[0] if parts else ""
    extracted["last_name"] = " ".join(parts[1:]) if len(parts) > 1 else ""
    return extracted


def _merge_ocr_results(primary: list, secondary: list, min_dist: float = 20.0) -> list:
    """Merge two OCR passes; skip secondary detections that overlap with primary ones."""
    merged = list(primary)
    for item in secondary:
        ix, iy = item["center"]
        if not any(
            abs(ix - p["center"][0]) < min_dist and abs(iy - p["center"][1]) < min_dist
            for p in primary
        ):
            merged.append(item)
    return merged


# ── Main entry point ──────────────────────────────────────────────────────────

def run_pipeline(image_bytes: bytes) -> Dict[str, Any]:
    """
    Run the full OCR pipeline on raw image bytes.

    The function never raises; errors are captured and reflected in the
    confidence score and issues dict so the API always returns a usable response.
    """
    # 1. Preprocess
    processed_img = None
    try:
        processed_img = preprocess(image_bytes)
    except Exception as exc:
        logger.error("Preprocessing failed: %s", exc)

    # 2. OCR — two-pass: Latin scripts first, then Arabic (separate readers required)
    ocr_results = []
    if processed_img is not None:
        try:
            ocr_results = run_ocr(processed_img, languages=["en", "fr"])
        except Exception as exc:
            logger.error("OCR engine failed (Latin pass): %s", exc)

        # Arabic pass — independent, failure does not discard Latin results
        try:
            ar_results = run_ocr(processed_img, languages=["en", "ar"])
            ocr_results = _merge_ocr_results(ocr_results, ar_results)
        except Exception as exc:
            logger.warning("OCR Arabic pass skipped: %s", exc)

    # Fallback: if preprocessing destroyed/degraded most text, retry on the raw decoded image.
    # Trigger when: fewer than 4 detections, OR all tokens are single chars (noise).
    _all_noise = len(ocr_results) > 0 and all(len(r["text"]) <= 2 for r in ocr_results)
    if len(ocr_results) < 4 or _all_noise:
        logger.warning(
            "Preprocessing degraded OCR (%d detections, all_noise=%s) — retrying on raw image",
            len(ocr_results), _all_noise,
        )
        try:
            from .preprocessor import _bytes_to_cv as _b2cv, _downscale_if_large as _dscale
            raw_img = _dscale(_b2cv(image_bytes))
            fb_latin = run_ocr(raw_img, languages=["en", "fr"])
            try:
                fb_arabic = run_ocr(raw_img, languages=["en", "ar"])
                fb_all = _merge_ocr_results(fb_latin, fb_arabic)
            except Exception:
                fb_all = fb_latin
            if len(fb_all) > len(ocr_results):
                logger.info("Raw-image fallback gave %d detections", len(fb_all))
                ocr_results = fb_all
        except Exception as exc:
            logger.warning("Raw-image OCR fallback failed: %s", exc)

    raw_text = _join_text(ocr_results)
    ocr_confidence = _avg_confidence(ocr_results)
    logger.info("OCR produced %d detections, avg confidence=%.2f", len(ocr_results), ocr_confidence)

    # 3. Extraction — three passes (line-proximity wins, spatial fills gaps, inline regex last)
    line_prox = extract_by_line_proximity(raw_text)
    spatial   = extract_fields_spatially(ocr_results)
    inline    = extract_inline_patterns(raw_text)

    # Priority: line_proximity > spatial > inline
    extracted = dict(inline)              # lowest priority base
    for k, v in spatial.items():         # spatial overwrites inline
        if v:
            extracted[k] = v
    for k, v in line_prox.items():       # line-proximity is highest priority
        if v:
            extracted[k] = v

    extracted = _split_full_name(extracted)

    # Stitch partial Arabic dates (e.g. "07" + "ماي 1994" across lines)
    _stitch_arabic_date(raw_text, extracted)

    # Sanity checks: discard obviously wrong values
    # nationality that is purely numeric is likely a misassigned personal code
    nat = extracted.get("nationality", "")
    # sex-code misreads: single letters, "MotIF", "F", "M", "MF", numbers
    _SEX_CODE_RE = __import__("re").compile(r"^(m|f|mf|fm|motif|natif|m/f|f/m|\d+)$", __import__("re").IGNORECASE)
    if nat and (nat.replace(" ", "").isdigit() or _SEX_CODE_RE.match(nat.strip())):
        logger.warning("Discarding invalid nationality value: %r", nat)
        extracted.pop("nationality", None)
        nat = ""

    # Nationality inference from document text keywords
    if not nat:
        rt_lower = raw_text.lower()
        tunisian_kw = ["الجمهورية التونسية", "التونسية", "TUNISIE", "TUNISIAN",
                       "بطاقةالتعرفالوطنيه", "بطاقة التعريف الوطنية",
                       "الجمهو"]  # partial "الجمهورية" for blurry images
        if any(kw in raw_text for kw in tunisian_kw) or "tunisie" in rt_lower or "tunisian" in rt_lower:
            extracted["nationality"] = "Tunisian"
        elif any(kw in raw_text for kw in ["LIETUVOS", "LIETUVA", "LITHUANIA"]) or "lietuva" in rt_lower:
            extracted["nationality"] = "Lithuanian"
        elif any(kw in raw_text for kw in ["FRANCE", "FRANÇAISE", "REPUBLIQUE FRANCAISE"]) or "française" in rt_lower:
            extracted["nationality"] = "French"
        elif any(kw in raw_text for kw in ["MAROC", "MAROCAIN", "\u0627\u0644\u0645\u063a\u0631\u0628\u064a\u0629"]):
            extracted["nationality"] = "Moroccan"

    # id_number that contains spaces or slashes is likely a misread label
    id_val = extracted.get("id_number", "")
    if id_val and (len(id_val) > 25 or "/" in id_val or ";" in id_val):
        logger.warning("Discarding noisy id_number: %r", id_val)
        extracted.pop("id_number", None)

    # 3b. Heuristic name fallback — only when both names still absent
    if not extracted.get("first_name") and not extracted.get("last_name"):
        heuristic = extract_names_heuristic(raw_text)
        for k, v in heuristic.items():
            if v and not extracted.get(k):
                extracted[k] = v
        logger.info("Heuristic name extraction applied: %s", heuristic)

    # 4. Validate and produce final score
    normalized, final_score, issues = validate_and_score(extracted)

    return {
        "first_name":    normalized.get("first_name", ""),
        "last_name":     normalized.get("last_name", ""),
        "date_of_birth": normalized.get("date_of_birth", ""),
        "expiry_date":   normalized.get("expiry_date", ""),
        "nationality":   normalized.get("nationality", ""),
        "id_number":     normalized.get("id_number", ""),
        "confidence":    final_score,
        "issues":        issues,
        "raw_ocr_text":  raw_text,
    }
