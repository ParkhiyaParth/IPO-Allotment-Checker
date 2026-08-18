import base64
import secrets

import pytest

from app.config import settings
from app.utils import encryption

_VALID_KEY = base64.b64encode(secrets.token_bytes(32)).decode()


def test_encrypt_decrypt_roundtrip(monkeypatch):
    monkeypatch.setattr(settings, "pan_encryption_key", _VALID_KEY)

    ciphertext = encryption.encrypt_pan("ABCDE1234F")

    assert ciphertext != "ABCDE1234F"
    assert encryption.decrypt_pan(ciphertext) == "ABCDE1234F"


def test_encrypt_raises_when_key_not_configured(monkeypatch):
    monkeypatch.setattr(settings, "pan_encryption_key", "")

    with pytest.raises(encryption.EncryptionNotConfiguredError):
        encryption.encrypt_pan("ABCDE1234F")


def test_encrypt_raises_when_key_wrong_length(monkeypatch):
    monkeypatch.setattr(settings, "pan_encryption_key", base64.b64encode(b"too-short").decode())

    with pytest.raises(encryption.EncryptionNotConfiguredError):
        encryption.encrypt_pan("ABCDE1234F")


def test_decrypt_fails_on_tampered_ciphertext(monkeypatch):
    monkeypatch.setattr(settings, "pan_encryption_key", _VALID_KEY)
    ciphertext = encryption.encrypt_pan("ABCDE1234F")

    raw = bytearray(base64.b64decode(ciphertext))
    raw[-1] ^= 0xFF  # flip a bit in the auth tag
    tampered = base64.b64encode(bytes(raw)).decode()

    # Tampered/corrupted ciphertext must not silently decrypt to garbage --
    # GCM's auth-tag check should raise instead.
    with pytest.raises(Exception):
        encryption.decrypt_pan(tampered)
