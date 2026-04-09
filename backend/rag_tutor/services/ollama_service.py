"""
Ollama-based RAG service (local LLM, no API limits).

Provides embeddings and text generation using locally-run Ollama.
Falls back to HuggingFace if Ollama is not available.
"""

import hashlib
import json
import logging
import os
import time
from typing import List, Dict, Optional

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_GEN_MODEL = os.getenv("OLLAMA_GEN_MODEL", "llama3.2:3b")

_CACHE_TTL_EMBED = 60 * 60 * 24 * 7  # 7 days
_CACHE_TTL_RESP = 60 * 60  # 1 hour

# System prompt for tutor mode
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


def _cache_key(prefix: str, text: str) -> str:
    """Generate cache key."""
    h = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"rag:{prefix}:{h}"


def _is_safe_output(text: str) -> bool:
    """Check if output contains unsafe financial advice."""
    lower = text.lower()
    return not any(phrase in lower for phrase in _UNSAFE_PHRASES)


_OLLAMA_AVAILABLE_CACHE: Optional[bool] = None
_OLLAMA_LAST_CHECK: float = 0.0
_OLLAMA_CHECK_TTL = 10.0  # re-check at most every 10 seconds


def _check_ollama_available() -> bool:
    """Check if Ollama is running locally. Results are cached for 10 s."""
    global _OLLAMA_AVAILABLE_CACHE, _OLLAMA_LAST_CHECK
    import time
    now = time.monotonic()
    if _OLLAMA_AVAILABLE_CACHE is not None and (now - _OLLAMA_LAST_CHECK) < _OLLAMA_CHECK_TTL:
        return _OLLAMA_AVAILABLE_CACHE
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=0.5)
        result = response.status_code == 200
    except Exception:
        result = False
    _OLLAMA_AVAILABLE_CACHE = result
    _OLLAMA_LAST_CHECK = now
    return result


# ── Ollama Embeddings ─────────────────────────────────────────────────────────

def get_embedding_ollama(text: str) -> Optional[List[float]]:
    """
    Get embedding using Ollama (local).
    Returns 768-dimensional embedding or None on failure.
    """
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={
                "model": OLLAMA_EMBED_MODEL,
                "prompt": text,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("embedding")
    except Exception as exc:
        logger.warning("Ollama embedding failed: %s", exc)
        return None


# ── HuggingFace Fallback ──────────────────────────────────────────────────────

def get_embedding_huggingface(text: str) -> Optional[List[float]]:
    """
    Fallback: Use sentence-transformers locally via HuggingFace.
    Uses multi-qa-MiniLM-L6-cos-v1 — a 384-dim model fine-tuned for
    asymmetric retrieval (query → passage), not just STS.
    No API required, runs on CPU.
    """
    global _hf_model
    try:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        if '_hf_model' not in globals() or _hf_model is None:
            _hf_model = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')

        embedding = _hf_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except ImportError:
        logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
        return None
    except Exception as exc:
        logger.error("HuggingFace embedding failed: %s", exc)
        # Reset so the next call retries a fresh model load instead of
        # using a potentially corrupt model instance.
        _hf_model = None
        return None


def get_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT", target_dim: int | None = None) -> List[float]:
    """
    Get text embedding with automatic fallback chain:
    1. Try Ollama (local, fast, unlimited)
    2. Fall back to HuggingFace (local, no API)
    3. Raise error if both fail

    ``target_dim`` — when set, cache AND live results that don't match this dim
    are rejected so we never mix vectors from different model families.
    This prevents stale 768-dim Ollama cache entries being served when only
    384-dim HuggingFace vectors are stored in the DB.

    Cache namespaces are model-specific (``emb_ol`` / ``emb_hf``) so switching
    between Ollama and HuggingFace never reuses incompatible cached vectors.
    """
    def _cached(namespace: str) -> Optional[List[float]]:
        ck = _cache_key(namespace, f"{task_type}:{text}")
        v = cache.get(ck)
        if v is None:
            return None
        if target_dim is not None and len(v) != target_dim:
            # Stale entry from a different model — evict it
            cache.delete(ck)
            return None
        return v

    def _store(namespace: str, v: List[float]) -> None:
        ck = _cache_key(namespace, f"{task_type}:{text}")
        cache.set(ck, v, _CACHE_TTL_EMBED)

    # ── Ollama ────────────────────────────────────────────────────────────────
    # Skip Ollama when caller knows stored vectors are 384-dim (HF) to avoid
    # producing a 768-dim query vector that would silently miss everything.
    skip_ollama = (target_dim is not None and target_dim != 768)

    if not skip_ollama:
        v = _cached("emb_ol")
        if v is not None:
            logger.debug("Embedding from Ollama cache (dim=%d)", len(v))
            return v

        if _check_ollama_available():
            embedding = get_embedding_ollama(text)
            if embedding and (target_dim is None or len(embedding) == target_dim):
                _store("emb_ol", embedding)
                logger.debug("Embedding from Ollama live (dim=%d)", len(embedding))
                return embedding

    # ── HuggingFace ───────────────────────────────────────────────────────────
    # Use "emb_hf2" as cache namespace so stale entries from the old
    # all-MiniLM-L6-v2 model (emb_hf) are not reused by multi-qa-MiniLM-L6-cos-v1.
    v = _cached("emb_hf2")
    if v is not None:
        logger.debug("Embedding from HuggingFace cache (dim=%d)", len(v))
        return v

    embedding = get_embedding_huggingface(text)
    # Retry once if failed (handles torch meta-tensor race during app startup)
    if embedding is None:
        import time as _time
        _time.sleep(1)
        embedding = get_embedding_huggingface(text)

    if embedding and (target_dim is None or len(embedding) == target_dim):
        _store("emb_hf2", embedding)
        logger.debug("Embedding from HuggingFace live (dim=%d)", len(embedding))
        return embedding

    raise RuntimeError(
        "All embedding services failed or produced incompatible dimensions. "
        "Install Ollama (https://ollama.ai) or sentence-transformers."
    )


# ── Text Generation ───────────────────────────────────────────────────────────

def generate_answer_ollama(prompt: str) -> Optional[str]:
    """Generate answer using Ollama."""
    try:
        response = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_GEN_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 1024,
                }
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except Exception as exc:
        logger.warning("Ollama generation failed: %s", exc)
        return None


def generate_answer_huggingface(prompt: str) -> Optional[str]:
    """
    Removed: TinyLlama on CPU took several minutes per response.
    Kept for interface compatibility but always returns None so callers
    fall through to the fast chunk-reader fallback.
    """
    return None


def _chunk_reader_answer(query: str, chunks: List[str]) -> str:
    """
    Instant fallback when no LLM is available: present the most relevant
    document excerpts as a structured answer with a clear header.
    This is always fast (no model inference required).
    """
    intro = (
        f"Here is what your documents say about \"{query}\":\n\n"
        if "?" not in query else
        "Based on your uploaded documents:\n\n"
    )
    body = "\n\n---\n\n".join(
        f"[Excerpt {i + 1}]\n{chunk.strip()}"
        for i, chunk in enumerate(chunks[:3])
    )
    footer = (
        "\n\n---\n"
        "Tip: Install Ollama (https://ollama.ai) and run `ollama pull llama3.2:3b` "
        "to get AI-generated explanations instead of raw excerpts."
    )
    return intro + body + footer


def generate_answer(query: str, context_chunks: List[str], user_id: str) -> Dict:
    """
    Generate educational answer with automatic fallback:
    1. Try Ollama (local, unlimited)
    2. Fast chunk-reader (instant — returns formatted excerpts)

    TinyLlama/CPU generation has been removed: it took several minutes per
    response with no visible progress, making the UI appear frozen.

    Returns:
        {"answer": str, "sources": list, "cached": bool, "provider": str}
    """
    chunks_to_use = context_chunks[:5]
    context = "\n\n---\n\n".join(
        f"[Excerpt {i + 1}]:\n{chunk}" for i, chunk in enumerate(chunks_to_use)
    )

    # Cache key
    ck = _cache_key("resp", f"{user_id}:{query}:{context}")
    cached_resp = cache.get(ck)
    if cached_resp:
        result = json.loads(cached_resp)
        result["cached"] = True
        return result

    prompt = _SYSTEM_PROMPT.format(context=context, query=query)

    # Token guard
    if len(prompt) > 112_000:
        chunks_to_use = context_chunks[:3]
        context = "\n\n---\n\n".join(
            f"[Excerpt {i + 1}]:\n{chunk}" for i, chunk in enumerate(chunks_to_use)
        )
        prompt = _SYSTEM_PROMPT.format(context=context, query=query)

    # ── Try Ollama (fast, local LLM) ──────────────────────────────────────────
    if _check_ollama_available():
        answer_text = generate_answer_ollama(prompt)
        if answer_text and _is_safe_output(answer_text):
            result = {
                "answer":   answer_text,
                "sources":  [],
                "cached":   False,
                "provider": "Ollama (local)",
            }
            cache.set(ck, json.dumps(result), _CACHE_TTL_RESP)
            return result

    # ── Fallback: instant chunk-reader (no LLM inference) ─────────────────────
    answer_text = _chunk_reader_answer(query, chunks_to_use)
    result = {
        "answer":   answer_text,
        "sources":  [],
        "cached":   False,
        "provider": "chunk-reader",
    }
    # Cache briefly so repeated identical queries are instant
    cache.set(ck, json.dumps(result), 60 * 5)
    return result


# ── SSE Streaming Generation ──────────────────────────────────────────────────

def generate_answer_stream(query: str, context_chunks: List[str], user_id: str):
    """
    Generator that yields SSE-formatted lines for a streaming response.

    Each yielded string is either:
        data: {"token": "<text>"}\n\n
    or the final event:
        data: {"done": true, "provider": "<name>"}\n\n

    Falls back to word-by-word streaming of a blocking ``generate_answer``
    call when Ollama is not available.
    """
    chunks_to_use = context_chunks[:5]
    context = "\n\n---\n\n".join(
        f"[Excerpt {i + 1}]:\n{chunk}" for i, chunk in enumerate(chunks_to_use)
    )
    prompt = _SYSTEM_PROMPT.format(context=context, query=query)

    if len(prompt) > 112_000:
        chunks_to_use = context_chunks[:3]
        context = "\n\n---\n\n".join(
            f"[Excerpt {i + 1}]:\n{chunk}" for i, chunk in enumerate(chunks_to_use)
        )
        prompt = _SYSTEM_PROMPT.format(context=context, query=query)

    # ── Ollama native streaming ───────────────────────────────────────────────
    if _check_ollama_available():
        try:
            response = requests.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_GEN_MODEL,
                    "prompt": prompt,
                    "stream": True,
                    "options": {"temperature": 0.2, "num_predict": 1024},
                },
                stream=True,
                timeout=120,
            )
            response.raise_for_status()

            full_text = ""
            for raw_line in response.iter_lines():
                if not raw_line:
                    continue
                try:
                    chunk_data = json.loads(raw_line)
                    token = chunk_data.get("response", "")
                    if token:
                        full_text += token
                        yield f"data: {json.dumps({'token': token})}\n\n"
                    if chunk_data.get("done"):
                        break
                except Exception:  # noqa: BLE001
                    continue

            if not _is_safe_output(full_text):
                safety_msg = " [Response filtered: contains disallowed content]"
                yield f"data: {json.dumps({'token': safety_msg})}\n\n"

            yield f"data: {json.dumps({'done': True, 'provider': 'Ollama (local)'})}\n\n"
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning("Ollama streaming failed (%s) — falling back to blocking gen", exc)

    # ── Fallback: blocking generate → word-by-word SSE ────────────────────────
    result = generate_answer(query, context_chunks, user_id)
    answer = result.get("answer", "")
    provider = result.get("provider", "unknown")

    words = answer.split(" ")
    for i, word in enumerate(words):
        token = word + (" " if i < len(words) - 1 else "")
        yield f"data: {json.dumps({'token': token})}\n\n"

    yield f"data: {json.dumps({'done': True, 'provider': provider})}\n\n"
