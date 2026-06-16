"""
Validation layer.

Responsibilities:
  - Normalise date strings to YYYY-MM-DD
  - Validate ID number format
  - Check required fields are present
  - Compute a final confidence score based on issues found
"""

import re
from typing import Dict, List, Optional, Tuple

_DATE_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_DSLASH = re.compile(r"^(\d{2})[/\-.](\d{2})[/\-.](\d{4})$")
_DATE_ISO_SLASH = re.compile(r"^(\d{4})[/\-.](\d{2})[/\-.](\d{2})$")
_ID_RE = re.compile(r"^[A-Z0-9\s\-./]{4,30}$", re.IGNORECASE)

# Arabic and French month name → zero-padded month number
_NAMED_MONTHS: Dict[str, str] = {
    # Arabic (Maghreb variant / Modern Standard)
    "\u064a\u0646\u0627\u064a\u0631": "01", "\u062c\u0627\u0646\u0641\u064a": "01",
    "\u0641\u0628\u0631\u0627\u064a\u0631": "02", "\u0641\u064a\u0641\u0631\u064a": "02",
    "\u0645\u0627\u0631\u0633": "03",
    "\u0623\u0628\u0631\u064a\u0644": "04", "\u0623\u0641\u0631\u064a\u0644": "04",
    "\u0645\u0627\u064a\u0648": "05", "\u0645\u0627\u064a": "05",
    "\u064a\u0648\u0646\u064a\u0648": "06", "\u062c\u0648\u0627\u0646": "06",
    "\u064a\u0648\u0644\u064a\u0648": "07", "\u062c\u0648\u064a\u0644\u064a\u0629": "07",
    "\u0623\u063a\u0633\u0637\u0633": "08", "\u0623\u0648\u062a": "08",
    "\u0633\u0628\u062a\u0645\u0628\u0631": "09",
    "\u0623\u0643\u062a\u0648\u0628\u0631": "10",
    "\u0646\u0648\u0641\u0645\u0628\u0631": "11",
    "\u062f\u064a\u0633\u0645\u0628\u0631": "12",
    # French
    "janvier": "01",
    "f\u00e9vrier": "02", "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "ao\u00fbt": "08", "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "d\u00e9cembre": "12", "decembre": "12",
}

# "07 ماي 1994"  or  "07 mai 1994"  or  "07 MAI 1994"
_DATE_NAMED_MONTH = re.compile(
    r"(\d{1,2})\s+([\w\u0600-\u06ff]+)\s+(\d{4})",
    re.IGNORECASE | re.UNICODE,
)


# ── Date normalisation ────────────────────────────────────────────────────────

def normalize_date(raw: str) -> str:
    """
    Try to convert common date representations to YYYY-MM-DD.
    Returns the input unchanged when the format is unrecognised.
    Handles:
    - DD/MM/YYYY, YYYY-MM-DD, DD.MM.YYYY
    - DD MM YYYY (space-separated, Lithuanian-style)
    - "07 ماي 1994" / "07 mai 1994" (Arabic/French month names)
    """
    if not raw:
        return ""
    raw = raw.strip()

    # ── Named-month dates (Arabic / French) before any separator stripping ──
    m = _DATE_NAMED_MONTH.search(raw)
    if m:
        day, month_name, year = m.group(1), m.group(2), m.group(3)
        month_num = _NAMED_MONTHS.get(month_name.lower()) or _NAMED_MONTHS.get(month_name)
        if month_num:
            return f"{year}-{month_num}-{day.zfill(2)}"

    # Normalise separators: backtick, dot, space → slash for uniform parsing
    normalized = raw.replace("`", "/").replace(".", "/")

    # Already ISO-8601
    if _DATE_ISO.match(normalized):
        return normalized

    # YYYY/MM/DD or YYYY-MM-DD variants
    m = _DATE_ISO_SLASH.match(normalized)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # DD/MM/YYYY or DD-MM-YYYY or DD.MM.YYYY
    m = _DATE_DSLASH.match(normalized)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        return f"{year}-{month}-{day}"

    # DD MM YYYY (space-separated, e.g. Lithuanian cards)
    m = re.match(r"^(\d{2})\s+(\d{2})\s+(\d{4})$", raw)
    if m:
        day, month, year = m.group(1), m.group(2), m.group(3)
        return f"{year}-{month}-{day}"

    return raw  # unrecognised — return as-is


# ── Field validators ─────────────────────────────────────────────────────────

def _validate_date(date_str: str) -> bool:
    """True if date_str looks like a valid YYYY-MM-DD."""
    if not date_str or not _DATE_ISO.match(date_str):
        return False
    _, m, d = date_str.split("-")
    return 1 <= int(m) <= 12 and 1 <= int(d) <= 31


def _validate_id_number(id_number: str) -> bool:
    """Basic alphanumeric check — 4 to 30 characters after removing separators."""
    if not id_number:
        return False
    cleaned = re.sub(r"[\s\-.]", "", id_number)
    return bool(_ID_RE.match(cleaned)) and 4 <= len(cleaned) <= 30


# ── Main entry ───────────────────────────────────────────────────────────────

def validate_and_score(extracted: Dict) -> Tuple[Dict, float, Dict[str, str]]:
    """
    Validate and normalise extracted fields.

    Returns
    -------
    normalized   : dict with date fields in YYYY-MM-DD
    score        : float 0-1  (penalised for missing/invalid fields)
    issues       : dict field → human-readable problem description
    """
    issues: Dict[str, str] = {}
    score = 1.0
    normalized = dict(extracted)

    # Normalise + validate date fields
    for date_field in ("date_of_birth", "expiry_date"):
        raw = extracted.get(date_field, "")
        if raw:
            normalized[date_field] = normalize_date(raw)
            if not _validate_date(normalized[date_field]):
                issues[date_field] = f"Unrecognised date format: {raw!r}"
                score -= 0.10

    # Validate ID number
    id_num = extracted.get("id_number", "")
    if id_num:
        if not _validate_id_number(id_num):
            issues["id_number"] = f"Possibly malformed: {id_num!r}"
            score -= 0.15
    else:
        issues["id_number"] = "Missing"
        score -= 0.20

    # Required name fields
    for field in ("first_name", "last_name"):
        if not extracted.get(field):
            issues[field] = "Missing"
            score -= 0.15

    score = round(max(0.0, min(1.0, score)), 2)
    return normalized, score, issues
