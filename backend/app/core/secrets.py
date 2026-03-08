"""
Helpers for encrypting and masking runtime-managed secrets.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

settings = get_settings()


def _build_fernet() -> Fernet:
    key_material = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key_material))


def encrypt_secret(value: str) -> str:
    """Encrypt a secret before storing it in the database."""
    return _build_fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    """Decrypt a previously stored secret."""
    if not value:
        return None
    try:
        return _build_fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Stored secret cannot be decrypted with current SECRET_KEY.") from exc


def mask_secret(value: str | None) -> str | None:
    """Return a short masked summary for UI display."""
    if not value:
        return None
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:3]}***{value[-4:]}"
