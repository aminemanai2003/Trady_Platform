"""
Fernet-based encryption for face embedding vectors.

The 128-d (or 512-d) float array is serialized as JSON and encrypted
with AES-128-CBC (Fernet) before being stored in the database.
The plaintext embedding is NEVER persisted.

Key selection (in priority order):
  1. FACE_EMBEDDING_KEY env var — must be a valid 32-byte URL-safe base64 Fernet key.
  2. Derived from DJANGO_SECRET_KEY via PBKDF2-HMAC-SHA256 (100k iterations).

Generate a key with:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

import base64
import hashlib
import json
import logging
import os

logger = logging.getLogger(__name__)

_fernet_instance = None


def _get_fernet():
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance

    try:
        from cryptography.fernet import Fernet
    except ImportError:
        raise ImportError(
            "cryptography package is required for face embedding encryption.\n"
            "Install with: pip install cryptography"
        )

    env_key = os.getenv("FACE_EMBEDDING_KEY", "").strip()
    if env_key:
        try:
            instance = Fernet(env_key.encode())
            logger.debug("Face embedding encryption: using FACE_EMBEDDING_KEY from environment.")
        except Exception as exc:
            logger.error("Invalid FACE_EMBEDDING_KEY (%s) — falling back to derived key.", exc)
            instance = _derive_key(Fernet)
    else:
        logger.warning(
            "FACE_EMBEDDING_KEY not set. Deriving key from SECRET_KEY. "
            "Set a dedicated key in production: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
        instance = _derive_key(Fernet)

    _fernet_instance = instance
    return instance


def _derive_key(Fernet):
    from django.conf import settings

    dk = hashlib.pbkdf2_hmac(
        "sha256",
        settings.SECRET_KEY.encode(),
        b"face-embedding-salt-v1",
        iterations=100_000,
        dklen=32,
    )
    return Fernet(base64.urlsafe_b64encode(dk))


def encrypt_embedding(embedding: list) -> str:
    """
    Serialize and encrypt a face embedding vector.

    Args:
        embedding: list of floats (128-d or 512-d).

    Returns:
        UTF-8 Fernet token string suitable for storing in a TextField.
    """
    fernet = _get_fernet()
    payload = json.dumps(embedding, separators=(",", ":")).encode("utf-8")
    return fernet.encrypt(payload).decode("utf-8")


def decrypt_embedding(ciphertext: str) -> list:
    """
    Decrypt and deserialize a stored face embedding vector.

    Args:
        ciphertext: Fernet token string from the database.

    Returns:
        list of floats.

    Raises:
        cryptography.fernet.InvalidToken: If the token is invalid or tampered.
    """
    fernet = _get_fernet()
    raw = fernet.decrypt(
        ciphertext.encode("utf-8") if isinstance(ciphertext, str) else ciphertext
    )
    return json.loads(raw.decode("utf-8"))
