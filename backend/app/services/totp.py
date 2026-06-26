"""TOTP (RFC 6238) using only the stdlib — no pyotp dependency.

Secrets are stored encrypted at rest (Fernet, key derived from the app secret).
Compatible with Google Authenticator / Authy (SHA1, 6 digits, 30s period).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from urllib.parse import quote

_B32_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def random_base32(length: int = 32) -> str:
    """Length must be a multiple of 8 so the base32 secret needs no padding."""
    return "".join(secrets.choice(_B32_ALPHABET) for _ in range(length))


def _hotp(secret_b32: str, counter: int) -> str:
    pad = "=" * ((8 - len(secret_b32) % 8) % 8)
    key = base64.b32decode(secret_b32 + pad, casefold=True)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = (struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF) % 1_000_000
    return f"{code:06d}"


def verify(secret_b32: str, code: str, window: int = 1, at: float | None = None) -> bool:
    if not secret_b32 or not code:
        return False
    code = code.strip().replace(" ", "")
    if not code.isdigit():
        return False
    counter = int((at if at is not None else time.time()) // 30)
    for w in range(-window, window + 1):
        if hmac.compare_digest(_hotp(secret_b32, counter + w), code):
            return True
    return False


def provisioning_uri(secret_b32: str, email: str, issuer: str = "Scanix") -> str:
    label = quote(f"{issuer}:{email}")
    return f"otpauth://totp/{label}?secret={secret_b32}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"


def generate_backup_codes(n: int = 8) -> list[str]:
    return [secrets.token_hex(4) for _ in range(n)]


# ── Secret encryption at rest (Fernet) ─────────────────────────────────────────
def _fernet():
    from cryptography.fernet import Fernet

    raw = (
        os.getenv("TOTP_ENC_KEY")
        or os.getenv("JWT_SECRET")
        or os.getenv("SECRET_KEY")
        or "scanix-dev-totp-secret"
    ).encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(raw).digest())
    return Fernet(key)


def encrypt_secret(secret_b32: str) -> str:
    return _fernet().encrypt(secret_b32.encode()).decode()


def decrypt_secret(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()
