"""Password hashing, JWT tokens and AES-256 field encryption helpers."""
from __future__ import annotations

import base64
import binascii
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Token types
ACCESS = "access"
REFRESH = "refresh"


# --------------------------------------------------------------------------
# Passwords
# --------------------------------------------------------------------------
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# --------------------------------------------------------------------------
# JWT
# --------------------------------------------------------------------------
def _create_token(
    subject: str, token_type: str, expires: timedelta, version: int
) -> str:
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "ver": version,
        "iat": now,
        "exp": now + expires,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(subject: str, version: int = 0) -> str:
    return _create_token(
        subject, ACCESS, timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES), version
    )


def create_refresh_token(subject: str, version: int = 0) -> str:
    return _create_token(
        subject, REFRESH, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS), version
    )


def decode_token(token: str) -> dict[str, Any]:
    """Decode & verify a JWT. Raises jwt.PyJWTError on failure."""
    return jwt.decode(
        token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
    )


# --------------------------------------------------------------------------
# AES-256 field encryption (Fernet uses AES-128-CBC + HMAC; for a strict
# AES-256-GCM implementation swap in `cryptography.hazmat` AESGCM). Fernet is
# used here for a safe, authenticated default with key rotation support.
# --------------------------------------------------------------------------
def _fernet() -> Fernet:
    key = settings.DATA_ENCRYPTION_KEY
    if not key:
        raise RuntimeError("DATA_ENCRYPTION_KEY is not configured")
    # Use the value as-is if it is already a valid Fernet key; otherwise derive
    # a deterministic 32-byte key from it (SHA-256), so any passphrase works.
    try:
        return Fernet(key.encode())
    except (ValueError, binascii.Error):
        digest = hashlib.sha256(key.encode()).digest()
        return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_field(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet().encrypt(value.encode()).decode()


def decrypt_field(token: str | None) -> str | None:
    if token is None:
        return None
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        return None
