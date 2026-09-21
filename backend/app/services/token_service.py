"""Opaque, hashed, expiring one-use tokens. Caller owns the transaction."""
import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.models.user import RecoveryToken, User

EMAIL_VERIFY = "email_verify"
PASSWORD_RESET = "password_reset"


def create_purpose_token(subject: str, purpose: str, hours: int = 24, *, db: Session) -> str:
    token = secrets.token_urlsafe(32)
    db.add(RecoveryToken(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                        user_id=int(subject), purpose=purpose,
                        expires_at=datetime.now(UTC) + timedelta(hours=hours)))
    db.flush()
    return token


def consume_purpose_token(token: str, purpose: str, db: Session) -> User | None:
    digest = hashlib.sha256(token.encode()).hexdigest()
    row = db.get(RecoveryToken, digest)
    if row is None:
        return None
    # Serialize account updates on PostgreSQL as well as token consumption.
    user = db.scalar(select(User).where(User.id == row.user_id).with_for_update())
    if user is None or not user.is_active:
        return None
    now = datetime.now(UTC)
    result = db.execute(update(RecoveryToken).where(
        RecoveryToken.token_hash == digest, RecoveryToken.purpose == purpose,
        RecoveryToken.consumed_at.is_(None), RecoveryToken.expires_at > now
    ).values(consumed_at=now).execution_options(synchronize_session=False))
    return user if result.rowcount == 1 else None
