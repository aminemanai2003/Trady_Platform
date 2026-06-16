"""
Gemini API service — embeddings + generation.

Uses the official Google GenAI SDK (`google-genai` package).
Implements:
  - Embedding with `gemini-embedding-001` (768 dimensions)
  - Generation with `gemini-2.0-flash` (tutor-mode, no financial advice)
  - Retry logic for rate limits (exponential backoff)
  - Redis/Django cache for embeddings (7 days) and responses (1 hour)
"""

import hashlib
import json
import logging
import os
import time

from google import genai
from google.genai import types
from django.core.cache import cache

logger = logging.getLogger(__name__)

_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Initialize Gemini client (API key from environment)
_client = None

def _get_client():
    """Lazy-load Gemini client."""
    global _client
    if _client is None:
        if not _API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set in the environment.")
        _client = genai.Client(api_key=_API_KEY)
    return _client

_CACHE_TTL_EMBED = 60 * 60 * 24 * 7    # 7 days
_CACHE_TTL_RESP  = 60 * 60              # 1 hour
_MAX_RETRIES     = 3

_EMBED_MODEL = "gemini-embedding-001"
_GEN_MODEL   = "gemini-1.5-flash"  # More stable for free tier


# ── Helpers ───────────────────────────────────────────────────────────────────

def _cache_key(prefix: str, text: str) -> str:
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"rag:{prefix}:{h}"


# ── Embedding ─────────────────────────────────────────────────────────────────

def get_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> list:
    """
    Embed text using Gemini gemini-embedding-001.
    Returns list of 768 floats.
    Raises RuntimeError on failure.
    """
    client = _get_client()

    ck = _cache_key("emb", f"{task_type}:{text}")
    cached = cache.get(ck)
    if cached is not None:
        return cached

    for attempt in range(_MAX_RETRIES):
        try:
            result = client.models.embed_content(
                model=_EMBED_MODEL,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type=task_type,
                    output_dimensionality=768
                )
            )
            
            # Extract embedding values
            if result.embeddings and len(result.embeddings) > 0:
                values = result.embeddings[0].values
                cache.set(ck, values, _CACHE_TTL_EMBED)
                return values
            else:
                raise RuntimeError("No embeddings returned from Gemini API")
                
        except Exception as exc:
            # Check for rate limiting
            exc_str = str(exc).lower()
            if "429" in exc_str or "rate" in exc_str or "quota" in exc_str:
                wait = 2 ** attempt
                logger.warning("Gemini embed rate-limited — waiting %ds (attempt %d)", wait, attempt + 1)
                time.sleep(wait)
                continue
                
            if attempt == _MAX_RETRIES - 1:
                logger.error("Gemini embed API failed after %d attempts: %s", _MAX_RETRIES, exc)
                raise RuntimeError(f"Gemini embed API failed after {_MAX_RETRIES} attempts: {exc}") from exc
            time.sleep(2 ** attempt)

    raise RuntimeError("Gemini embed API: max retries exceeded")


# ── System prompt (tutor mode) ────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a trading education tutor. Your ONLY job is to explain trading concepts \
using the document excerpts provided below.

STRICT RULES:
1. ONLY answer using the document context below — never from general knowledge.
2. If the answer is NOT in the context, respond EXACTLY:
   "This topic is not covered in your uploaded documents."
3. NEVER give financial advice, direct buy/sell signals, or price predictions.
4. NEVER use phrases like "buy now", "sell now", "guaranteed profit", \
"risk-free investment", "invest now", "sure bet", or similar.
5. Explain concepts in clear, simple language with examples when helpful.
6. You are a TUTOR, not a financial advisor.

DOCUMENT CONTEXT:
{context}

USER QUESTION: {query}

Provide a clear educational explanation based solely on the document context above.\
"""

_UNSAFE_PHRASES = [
    "buy now", "sell now", "guaranteed profit", "100% profit",
    "risk-free", "buy this stock", "sell this stock",
    "invest now", "sure bet", "you should buy", "you should sell",
]


def _is_safe_output(text: str) -> bool:
    lower = text.lower()
    return not any(phrase in lower for phrase in _UNSAFE_PHRASES)


# ── Generation ────────────────────────────────────────────────────────────────

def generate_answer(query: str, context_chunks: list, user_id: str) -> dict:
    """
    Generate an educational answer using Gemini Flash.

    Args:
        query          — the user's question
        context_chunks — list of relevant text chunks (max 5 used)
        user_id        — used for cache key scoping

    Returns:
        {"answer": str, "sources": list, "cached": bool}
    """
    try:
        client = _get_client()
    except RuntimeError:
        return {
            "answer":  "AI service not configured. Please set GEMINI_API_KEY.",
            "sources": [],
            "cached":  False,
        }

    # Use at most 5 chunks to stay within free-tier token limits
    chunks_to_use = context_chunks[:5]
    context = "\n\n---\n\n".join(
        f"[Excerpt {i + 1}]:\n{chunk}" for i, chunk in enumerate(chunks_to_use)
    )

    # Cache key includes user + query + context fingerprint
    ck = _cache_key("resp", f"{user_id}:{query}:{context}")
    cached_resp = cache.get(ck)
    if cached_resp:
        result = json.loads(cached_resp)
        result["cached"] = True
        return result

    prompt = _SYSTEM_PROMPT.format(context=context, query=query)

    # Rough token guard — ~4 chars per token; keep under 28 k tokens
    if len(prompt) > 112_000:
        chunks_to_use = context_chunks[:3]
        context = "\n\n---\n\n".join(
            f"[Excerpt {i + 1}]:\n{chunk}" for i, chunk in enumerate(chunks_to_use)
        )
        prompt = _SYSTEM_PROMPT.format(context=context, query=query)

    for attempt in range(_MAX_RETRIES):
        try:
            response = client.models.generate_content(
                model=_GEN_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    max_output_tokens=1024,
                    temperature=0.2,
                    top_p=0.8,
                    safety_settings=[
                        types.SafetySetting(
                            category="HARM_CATEGORY_DANGEROUS_CONTENT",
                            threshold="BLOCK_MEDIUM_AND_ABOVE",
                        ),
                    ],
                )
            )

            # Extract answer text
            if response.text:
                answer_text = response.text.strip()

                if not _is_safe_output(answer_text):
                    answer_text = (
                        "This topic is not covered in your uploaded documents "
                        "in a way I can safely explain."
                    )

                result = {"answer": answer_text, "sources": [], "cached": False}
                cache.set(ck, json.dumps(result), _CACHE_TTL_RESP)
                return result
            else:
                return {
                    "answer":  "The AI could not generate a response. Please try again.",
                    "sources": [],
                    "cached":  False,
                }

        except Exception as exc:
            # Check for rate limiting
            exc_str = str(exc).lower()
            if "429" in exc_str or "rate" in exc_str or "quota" in exc_str:
                wait = 2 ** (attempt + 1)
                logger.warning("Gemini gen rate-limited — waiting %ds", wait)
                time.sleep(wait)
                continue
                
            if attempt == _MAX_RETRIES - 1:
                logger.error("Gemini gen API failed: %s", exc)
                return {
                    "answer":  "AI service temporarily unavailable. Please try again in a moment.",
                    "sources": [],
                    "cached":  False,
                }
            time.sleep(2 ** attempt)

    return {
        "answer":  "AI service failed after multiple retries. Please try again.",
        "sources": [],
        "cached":  False,
    }
