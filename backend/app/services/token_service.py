"""Short-lived signed tokens for email verification and password reset.

These are stateless JWTs with a dedicated `type` claim, so no extra table is
needed. In production you may prefer single-use tokens stored in the DB.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings

EMAIL_VERIFY = "email_verify"
PASSWORD_RESET = "password_reset"


def create_purpose_token(subject: str, purpose: str, hours: int = 24) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "type": purpose,
        "iat": now,
        "exp": now + timedelta(hours=hours),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_purpose_token(token: str, purpose: str) -> str | None:
    """Return the subject if valid & matching purpose, else None."""
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
    except jwt.PyJWTError:
        return None
    if payload.get("type") != purpose:
        return None
    return payload.get("sub")
