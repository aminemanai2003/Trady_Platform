"""
Spatial field extraction module.

Strategy
--------
1. Walk each OCR detection and check whether its text matches a known label.
2. If it does, search for the nearest value that is:
     - to the *right*  of the label on roughly the same line, OR
     - *below* the label in roughly the same column.
3. Inline regex patterns act as a secondary pass on the full joined text.
4. Spatial results take priority over inline results.

Multilingual label normalisation
---------------------------------
Arabic, French, and English label variants are all mapped to a small set
of canonical field names (first_name, last_name, date_of_birth, …).
"""

import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional

# ── Label → canonical field name ────────────────────────────────────────────

LABEL_MAP: Dict[str, str] = {
    # ╌ last name ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
    "nom":             "last_name",
    "name":            "last_name",
    "surname":         "last_name",
    "last name":       "last_name",
    "family name":     "last_name",
    "اللقب":           "last_name",   # Tunisian CIN: family name
    "اسم العائلة":     "last_name",
    "nom de famille":  "last_name",
    # ╌ first name ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
    "prenom":          "first_name",
    "prénom":          "first_name",
    "given name":      "first_name",
    "given names":     "first_name",
    "first name":      "first_name",
    "الاسم":           "first_name",  # Arabic: given name (NOT family name)
    "الاسم الشخصي":   "first_name",
    "الاسم الأول":    "first_name",
    # ╌ full name (fallback — split later) ╌╌╌╌╌╌╌╌╌╌╌╌╌
    "full name":       "full_name",
    "الاسم الكامل":   "full_name",
    # ╌ date of birth ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
    "date of birth":   "date_of_birth",
    "dob":             "date_of_birth",
    "birth date":      "date_of_birth",
    "born":            "date_of_birth",
    "né le":           "date_of_birth",
    "ne le":           "date_of_birth",
    "تاريخ الولادة":  "date_of_birth",
    "تاريخ الميلاد":  "date_of_birth",
    # ╌ place of birth ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
    "مكانها":          "place_of_birth",
    "مكان الولادة":    "place_of_birth",
    "lieu de naissance": "place_of_birth",
    # ╌ nationality ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
    "nationality":     "nationality",
    "nationalité":     "nationality",
    "nationalite":     "nationality",
    "الجنسية":         "nationality",
    # ╌ id / document number ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
    "id number":       "id_number",
    "id no":           "id_number",
    "document number": "id_number",
    "number":          "id_number",
    "no":              "id_number",
    "رقم الوثيقة":    "id_number",
    "رقم الهوية":     "id_number",
    "رقم البطاقة":    "id_number",
    "cin":             "id_number",
    "license number":  "id_number",
    "driver license":  "id_number",
    # ╌ expiry ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
    "expiry":          "expiry_date",
    "expiry date":     "expiry_date",
    "expiration":      "expiry_date",
    "expires":         "expiry_date",
    "valid until":     "expiry_date",
    "exp":             "expiry_date",
    "صالحة حتى":       "expiry_date",
    "تاريخ الانتهاء":  "expiry_date",
    # ╌ Lithuanian labels ╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌╌
    "pavardė":         "last_name",
    "pavarde":         "last_name",
    "vardas":          "first_name",
    "vardai":          "first_name",
    "gimimo data":     "date_of_birth",
    "pilietybė":       "nationality",
    "pilietybe":       "nationality",
    "galioja iki":     "expiry_date",
    "asmens kodas":    "id_number",
    # ╌ generic compound-label parts (after slash-split) ╌
    "personal no":     "id_number",
    "personal code":   "id_number",
    "personal na":     "id_number",
    "document no":     "id_number",
    "card no":         "id_number",
    "card no:":        "id_number",
}


def _fuzzy_label_match(text: str, threshold: float = 0.78) -> Optional[str]:
    """
    Fuzzy-match text against all known labels (handles OCR typos in Arabic labels).
    Only considers labels with length >= 4 to avoid false positives on short words.
    Returns canonical field name or None.
    """
    cleaned = text.strip().strip(":\u200f\u200e").lower()
    if len(cleaned) < 4:
        return None
    best_ratio = 0.0
    best_field = None
    for label, field in LABEL_MAP.items():
        if len(label) < 4:
            continue
        ratio = SequenceMatcher(None, cleaned, label.lower()).ratio()
        if ratio >= threshold and ratio > best_ratio:
            best_ratio = ratio
            best_field = field
    # Also try against raw (non-lowercased) for Arabic
    arabic_text = text.strip().strip(":\u200f\u200e")
    for label, field in LABEL_MAP.items():
        if len(label) < 4:
            continue
        ratio = SequenceMatcher(None, arabic_text, label).ratio()
        if ratio >= threshold and ratio > best_ratio:
            best_ratio = ratio
            best_field = field
    return best_field


def _normalize_label(text: str) -> Optional[str]:
    """Return canonical field name if text matches a known label, else None.

    Handles:
    - compound labels like 'PAVARDĖ / SURNAME' split on '/' or '|'
    - Arabic right-to-left labels that may have leading/trailing colons
    - Fuzzy match for OCR typos (e.g. 'تايخ الولادة' → 'تاريخ الولادة')
    """
    cleaned = text.strip().strip(":\u200f\u200e")  # strip colon + RLM/LRM marks
    lower = cleaned.lower()
    if lower in LABEL_MAP:
        return LABEL_MAP[lower]
    # Arabic exact match before lower (Arabic is case-insensitive already)
    if cleaned in LABEL_MAP:
        return LABEL_MAP[cleaned]
    # Try each part of a slash/pipe-separated label
    for part in re.split(r"[/|]", lower):
        part = part.strip().strip(": ")
        if part and part in LABEL_MAP:
            return LABEL_MAP[part]
    # Arabic parts
    for part in re.split(r"[/|]", cleaned):
        part = part.strip().strip(": ")
        if part and part in LABEL_MAP:
            return LABEL_MAP[part]
    # Fuzzy fallback — catches OCR typos such as missing diacritics / char swaps
    return _fuzzy_label_match(cleaned)


def _is_value_candidate(text: str) -> bool:
    """Return True if the text looks like a value rather than a label."""
    return bool(text.strip()) and _normalize_label(text) is None


# ── Spatial relationship helpers ─────────────────────────────────────────────

def _dist(a: tuple, b: tuple) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


def _same_row(label: Dict, other: Dict, tol: float = 30.0) -> bool:
    return abs(label["center"][1] - other["center"][1]) < tol


def _same_col(label: Dict, other: Dict, tol: float = 40.0) -> bool:
    return abs(label["center"][0] - other["center"][0]) < tol


def _is_to_right(label: Dict, other: Dict) -> bool:
    return _same_row(label, other) and other["x_min"] > label["x_max"] - 5


def _is_to_left(label: Dict, other: Dict) -> bool:
    """RTL: value is to the LEFT of the label."""
    return _same_row(label, other) and other["x_max"] < label["x_min"] + 5


def _is_below(label: Dict, other: Dict) -> bool:
    return _same_col(label, other) and other["y_min"] > label["y_max"] - 5


# ── Spatial extraction ────────────────────────────────────────────────────────

def extract_fields_spatially(ocr_results: List[Dict[str, Any]]) -> Dict[str, str]:
    """
    Walk OCR detections and build a field→value dict using spatial proximity.
    Labels to the left of or above values are both handled.
    """
    extracted: Dict[str, str] = {}

    for item in ocr_results:
        field = _normalize_label(item["text"])
        if field is None:
            continue
        if field in extracted:
            continue  # first match wins

        # Find all candidate values spatially adjacent to this label
        # Support both LTR (right/below) and RTL (left) layouts
        candidates = [
            other
            for other in ocr_results
            if other is not item
            and _is_value_candidate(other["text"])
            and (_is_to_right(item, other) or _is_to_left(item, other) or _is_below(item, other))
        ]

        if not candidates:
            continue

        nearest = min(candidates, key=lambda c: _dist(item["center"], c["center"]))
        extracted[field] = nearest["text"].strip()

    return extracted


# ── Inline / regex extraction ─────────────────────────────────────────────────

_DATE_RE = re.compile(
    r"\b(\d{2}[\`\/\-. ]\d{2}[\`\/\-. ]\d{4}"
    r"|\d{4}[\`\/\-. ]\d{2}[\`\/\-. ]\d{2})\b"
)
# Labeled ID (with keyword prefix)
_ID_LABELED_RE = re.compile(
    r"(?:id\s*no\.?|license\s*no\.?|document\s*no\.?|personal\s*(?:no|code)\.?|number|no\.?|cin|asmens\s*kodas)"
    r"[:\s\-]*([A-Z0-9\-]{5,25})",
    re.IGNORECASE,
)
# Standalone long digit sequences that look like national ID numbers (8-15 digits)
_ID_DIGITS_RE = re.compile(r"\b(\d{8,15})\b")
_EMAIL_RE = re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+")
_PHONE_RE = re.compile(
    r"(?:\+\d{1,3}[\s.\-]?)?(?:\(?\d{2,4}\)?[\s.\-]?)?\d{3,4}[\s.\-]?\d{3,4}"
)

# Noise tokens that are NOT person names (country / document headers etc.)
_NON_NAME_RE = re.compile(
    r"republic|respublika|respublikos|respublika|lietuva|lithu|identity|card|"
    r"passport|specimen|ministry|interior|government|national|citizen|sample|"
    r"motif|mot/f|\bm\b|\bf\b",  # sex field misreads
    re.IGNORECASE,
)


def extract_inline_patterns(full_text: str) -> Dict[str, Optional[str]]:
    """
    Secondary pass: regex-based extraction on the full joined OCR text.
    Used when spatial extraction misses a field.
    """
    results: Dict[str, Optional[str]] = {}

    m = _ID_LABELED_RE.search(full_text)
    if m:
        results["id_number"] = m.group(1).strip()

    dates = _DATE_RE.findall(full_text)
    if dates:
        results.setdefault("date_of_birth", dates[0])
    if len(dates) > 1:
        results.setdefault("expiry_date", dates[1])

    # If only one date found and it is far in the future (>10 years from now),
    # it is almost certainly an expiry date, not a birth date.
    import datetime as _dt
    if len(dates) == 1 and results.get("date_of_birth") and not results.get("expiry_date"):
        try:
            from .validator import normalize_date as _nd
            iso = _nd(dates[0])
            if iso and iso[:4].isdigit() and int(iso[:4]) >= _dt.date.today().year + 5:
                results["expiry_date"] = results.pop("date_of_birth")
        except Exception:
            pass

    m = _EMAIL_RE.search(full_text)
    if m:
        results["email"] = m.group(0)

    m = _PHONE_RE.search(full_text)
    if m:
        results["phone"] = m.group(0)

    # Standalone long digit fallback for ID (e.g. Lithuanian personal code 11 digits)
    if not results.get("id_number"):
        m = _ID_DIGITS_RE.search(full_text)
        if m:
            results["id_number"] = m.group(1)

    return results


_ARABIC_CHAR_RE = re.compile(r"[\u0600-\u06ff]")
# Arabic tokens that are NOT names (document header / noise words)
_ARABIC_NON_NAME_RE = re.compile(
    r"بطاقة|الجمهورية|التعريف|الوطنية|الوطنيه|جمهوري|الهوية|الجنسية|تاريخ|الولادة|مكان",
    re.UNICODE,
)


def _looks_arabic_name(text: str) -> bool:
    """True if text looks like an Arabic personal name line (1-4 Arabic words, no digits)."""
    stripped = text.strip()
    if not _ARABIC_CHAR_RE.search(stripped):
        return False
    if re.search(r"\d", stripped):
        return False
    if _ARABIC_NON_NAME_RE.search(stripped):
        return False
    words = stripped.split()
    return 1 <= len(words) <= 4 and all(len(w) >= 2 for w in words)


def extract_names_heuristic(raw_text: str) -> Dict[str, str]:
    """
    Last-resort name extraction when spatial detection found no labels.

    Strategy: on EU/MENA ID cards the first all-caps non-noise line is usually
    the family name, the second is the given name(s).
    """
    result: Dict[str, str] = {}
    cap_lines = [
        line.strip()
        for line in raw_text.splitlines()
        if (
            line.strip()
            and line.strip().isupper()                 # all uppercase
            and len(line.strip()) >= 2                 # at least 2 chars
            and not line.strip().isdigit()             # not pure number
            and not _NON_NAME_RE.search(line)          # not a noise token
        )
    ]
    if len(cap_lines) >= 1:
        result["last_name"] = cap_lines[0]
    if len(cap_lines) >= 2:
        result["first_name"] = cap_lines[1]

    # Arabic name fallback: find lines that look like Arabic personal names
    # Used when label-based extraction fails (e.g. Tunisian CIN with garbled labels)
    if not result.get("first_name") or not result.get("last_name"):
        arabic_names = [
            line.strip()
            for line in raw_text.splitlines()
            if _looks_arabic_name(line.strip())
        ]
        # First Arabic name candidate → first_name (getven name on Tunisian CIN)
        if arabic_names and not result.get("first_name"):
            result["first_name"] = arabic_names[0]
        if len(arabic_names) >= 2 and not result.get("last_name"):
            result["last_name"] = arabic_names[1]

    # Sanity: if nationality looks like a sex code (single letter, MOT/F, etc.) discard it
    nat_val = result.get("nationality", "")
    if nat_val and re.search(r"^(M|F|MOT/?F|MotIF|MOT|MF)$", nat_val.strip(), re.I):
        result.pop("nationality", None)

    return result


def extract_by_line_proximity(raw_text: str) -> Dict[str, str]:
    """
    Line-proximity extraction supporting three patterns (strict priority order):

    1. Label-only line  →  value on the NEXT non-empty line  (highest priority)
       e.g.  SURNAME\\nBASANAVICIENÉ

    2. Inline colon separator  →  label: value on the same line
       e.g.  تاريخ الولادة: 07 ماي 1994

    3. Label prefix + trailing value  →  last resort, only on non-label lines
       e.g.  تايخ الولادة 07   (next line: ماي 1994)
    """
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    result: Dict[str, str] = {}

    for idx, line in enumerate(lines):

        # ── Pattern 1 (highest priority): full line is a known label ────────
        full_field = _normalize_label(line)
        if full_field is not None:
            if full_field not in result:
                for next_line in lines[idx + 1:]:
                    if not next_line:
                        continue
                    if _normalize_label(next_line) is not None:
                        break
                    result[full_field] = next_line.strip()
                    break
            continue  # never fall through to patterns 2/3 for full label lines

        # ── Pattern 2: "label: value" on a single line ──────────────────────
        if ":" in line:
            colon_pos = line.index(":")
            label_part = line[:colon_pos].strip()
            value_part = line[colon_pos + 1:].strip()
            if value_part:
                field = _normalize_label(label_part)
                if field and field not in result:
                    result[field] = value_part
                    continue

        # ── Pattern 3: label prefix + trailing value (only non-label lines) ─
        words = line.split()
        for split_pos in range(len(words) - 1, 0, -1):
            candidate_label = " ".join(words[:split_pos])
            leftover = " ".join(words[split_pos:]).strip()
            # Skip leftover beginning with "/" (label separator artefact)
            if not leftover or leftover.startswith("/"):
                continue
            field = _normalize_label(candidate_label)
            if field and field not in result:
                # Combine leftover with up-to-2 subsequent non-label lines
                next_vals = []
                for next_line in lines[idx + 1: idx + 3]:
                    if not next_line or _normalize_label(next_line) is not None:
                        break
                    next_vals.append(next_line)
                combined = leftover
                if next_vals:
                    combined += " " + " ".join(next_vals)
                result[field] = combined.strip()
                break

    return result


def merge_extractions(spatial: Dict, inline: Dict) -> Dict:
    """
    Merge spatial and inline results.
    Spatial values take priority (they are position-verified).
    """
    merged = {k: v for k, v in inline.items() if v}
    merged.update({k: v for k, v in spatial.items() if v})
    return merged
