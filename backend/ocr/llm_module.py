"""
LLM fallback module.

Calls Gemini ONLY when:
  - One or more required fields are still missing after spatial/regex extraction, OR
  - The average OCR confidence is below the threshold.

This keeps API costs low: most good-quality scans will never reach this module.
Uses the official Google GenAI SDK.
"""

import json
import logging
import os
import re
from typing import Dict, Optional

from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"first_name", "last_name", "id_number"}
CONFIDENCE_THRESHOLD = 0.55  # trigger LLM if OCR avg confidence < this

# Lazy-load client
_client = None

def _get_client():
    """Lazy-load Gemini client."""
    global _client
    if _client is None:
        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set")
        _client = genai.Client(api_key=api_key)
    return _client


def _needs_llm(extracted: Dict, ocr_confidence: float) -> bool:
    """Return True if the LLM fallback should be invoked."""
    missing = REQUIRED_FIELDS - {k for k, v in extracted.items() if v}
    return bool(missing) or ocr_confidence < CONFIDENCE_THRESHOLD


def _build_prompt(ocr_text: str) -> str:
    return (
        "You are an identity document parser.\n"
        "Given the raw OCR text below (possibly noisy), extract these fields.\n"
        "Return ONLY a valid JSON object — no markdown, no extra text.\n"
        "Fields: first_name, last_name, date_of_birth (YYYY-MM-DD if possible), "
        "nationality, id_number.\n"
        "Set any unknown field to null.\n\n"
        f"OCR TEXT:\n{ocr_text}"
    )


def call_gemini(ocr_text: str) -> Optional[Dict]:
    """
    Send cleaned OCR text to Gemini and return parsed JSON.
    Returns None on any failure so the caller can proceed without LLM data.
    """
    try:
        client = _get_client()
    except RuntimeError as exc:
        logger.warning("Gemini client error: %s — skipping LLM fallback", exc)
        return None

    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    
    try:
        response = client.models.generate_content(
            model=model,
            contents=_build_prompt(ocr_text),
            config=types.GenerateContentConfig(
                temperature=0,
                max_output_tokens=512,
            )
        )
        
        if response.text:
            raw_text = response.text.strip()
            # Strip markdown fences that the model sometimes adds
            cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text.strip())
            return json.loads(cleaned)
        else:
            logger.warning("Gemini returned no text")
            return None
            
    except Exception as exc:
        logger.error("Gemini LLM fallback failed: %s", exc)
        return None


def llm_fallback(extracted: Dict, ocr_text: str, ocr_confidence: float) -> Dict:
    """
    Conditionally invoke Gemini.

    LLM results fill gaps only; existing extracted values are always kept.
    """
    if not _needs_llm(extracted, ocr_confidence):
        logger.debug("LLM fallback skipped (confidence=%.2f, no missing fields)", ocr_confidence)
        return extracted

    logger.info("Invoking Gemini LLM fallback (confidence=%.2f)", ocr_confidence)
    llm_data = call_gemini(ocr_text)
    if not llm_data:
        return extracted

    # Merge: LLM fills gaps, existing values are preserved
    merged = {k: v for k, v in llm_data.items() if v}
    merged.update({k: v for k, v in extracted.items() if v})
    return merged
