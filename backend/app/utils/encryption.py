"""AES-256-GCM encryption for server-side-at-rest PAN storage (opt-in
zero-tap allotment discovery). Unrelated to linkintime_client.py's AES-128-
CBC usage -- that replicates a third-party site's own hardcoded, non-secret
transport scheme. Here PAN_ENCRYPTION_KEY is a real secret (backend/.env
only, never committed), and GCM is used instead of CBC so tampered or
corrupted ciphertext fails the auth-tag check loudly instead of silently
decrypting to garbage.
"""

import base64

from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

from app.config import settings

_NONCE_BYTES = 12
_TAG_BYTES = 16
_KEY_BYTES = 32


class EncryptionNotConfiguredError(Exception):
    pass


def _key_bytes() -> bytes:
    if not settings.pan_encryption_key:
        raise EncryptionNotConfiguredError("PAN_ENCRYPTION_KEY is not set in backend/.env")
    try:
        key = base64.b64decode(settings.pan_encryption_key, validate=True)
    except Exception as exc:
        raise EncryptionNotConfiguredError("PAN_ENCRYPTION_KEY is not valid base64") from exc
    if len(key) != _KEY_BYTES:
        raise EncryptionNotConfiguredError(f"PAN_ENCRYPTION_KEY must decode to {_KEY_BYTES} bytes (AES-256)")
    return key


def encrypt_pan(plaintext_pan: str) -> str:
    """Returns base64(nonce || ciphertext || tag) as a single opaque string."""
    cipher = AES.new(_key_bytes(), AES.MODE_GCM, nonce=get_random_bytes(_NONCE_BYTES))
    ciphertext, tag = cipher.encrypt_and_digest(plaintext_pan.encode("utf-8"))
    return base64.b64encode(cipher.nonce + ciphertext + tag).decode("ascii")


def decrypt_pan(encoded: str) -> str:
    raw = base64.b64decode(encoded)
    nonce, ciphertext, tag = raw[:_NONCE_BYTES], raw[_NONCE_BYTES:-_TAG_BYTES], raw[-_TAG_BYTES:]
    cipher = AES.new(_key_bytes(), AES.MODE_GCM, nonce=nonce)
    return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")
