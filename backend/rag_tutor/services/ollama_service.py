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


def _check_ollama_available() -> bool:
    """Check if Ollama is running locally."""
    try:
        response = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False


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
    No API required, runs on CPU.
    """
    try:
        from sentence_transformers import SentenceTransformer
        
        # Cache model in memory
        global _hf_model
        if '_hf_model' not in globals():
            _hf_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        embedding = _hf_model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except ImportError:
        logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
        return None
    except Exception as exc:
        logger.error("HuggingFace embedding failed: %s", exc)
        return None


def get_embedding(text: str, task_type: str = "RETRIEVAL_DOCUMENT") -> List[float]:
    """
    Get text embedding with automatic fallback chain:
    1. Try Ollama (local, fast, unlimited)
    2. Fall back to HuggingFace (local, no API)
    3. Raise error if both fail
    
    Returns list of floats (embedding vector).
    """
    ck = _cache_key("emb", f"{task_type}:{text}")
    cached = cache.get(ck)
    if cached is not None:
        return cached

    # Try Ollama first
    if _check_ollama_available():
        embedding = get_embedding_ollama(text)
        if embedding:
            cache.set(ck, embedding, _CACHE_TTL_EMBED)
            logger.debug("Embedding from Ollama (local)")
            return embedding

    # Fallback to HuggingFace
    embedding = get_embedding_huggingface(text)
    if embedding:
        cache.set(ck, embedding, _CACHE_TTL_EMBED)
        logger.debug("Embedding from HuggingFace (local)")
        return embedding

    raise RuntimeError(
        "All embedding services failed. "
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
    Fallback: Use HuggingFace transformers locally.
    Simple text generation with small models.
    """
    try:
        from transformers import pipeline
        
        # Cache model
        global _hf_gen_model
        if '_hf_gen_model' not in globals():
            _hf_gen_model = pipeline(
                "text-generation",
                model="TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                device=-1,  # CPU
            )
        
        result = _hf_gen_model(
            prompt,
            max_new_tokens=512,
            temperature=0.2,
            do_sample=True,
        )
        return result[0]["generated_text"].strip()
    except ImportError:
        logger.error("transformers not installed. Run: pip install transformers")
        return None
    except Exception as exc:
        logger.error("HuggingFace generation failed: %s", exc)
        return None


def generate_answer(query: str, context_chunks: List[str], user_id: str) -> Dict:
    """
    Generate educational answer with automatic fallback:
    1. Try Ollama (local, unlimited)
    2. Fall back to HuggingFace (local, basic)
    3. Return error message if both fail
    
    Returns:
        {"answer": str, "sources": list, "cached": bool, "provider": str}
    """
    # Use at most 5 chunks
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

    # Try Ollama first
    if _check_ollama_available():
        answer_text = generate_answer_ollama(prompt)
        if answer_text and _is_safe_output(answer_text):
            result = {
                "answer": answer_text,
                "sources": [],
                "cached": False,
                "provider": "Ollama (local)"
            }
            cache.set(ck, json.dumps(result), _CACHE_TTL_RESP)
            return result

    # Fallback to HuggingFace
    answer_text = generate_answer_huggingface(prompt)
    if answer_text:
        # Extract answer after prompt (HF returns full input+output)
        if prompt in answer_text:
            answer_text = answer_text.replace(prompt, "").strip()
        
        if _is_safe_output(answer_text):
            result = {
                "answer": answer_text,
                "sources": [],
                "cached": False,
                "provider": "HuggingFace (local)"
            }
            cache.set(ck, json.dumps(result), _CACHE_TTL_RESP)
            return result

    # Both failed
    return {
        "answer": (
            "AI service temporarily unavailable. "
            "Please install Ollama (https://ollama.ai) for local AI, "
            "or wait and try again later."
        ),
        "sources": [],
        "cached": False,
        "provider": "none"
    }
