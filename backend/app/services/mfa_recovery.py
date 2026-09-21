"""MFA backup code issuance/consumption share the caller's transaction."""
import hashlib
import re
import secrets
from datetime import UTC, datetime

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.models.user import MFARecoveryCode


def digest(code: str) -> str:
    return hashlib.sha256(code.encode("ascii")).hexdigest()


def issue(db: Session, user_id: int) -> list[str]:
    db.execute(delete(MFARecoveryCode).where(MFARecoveryCode.user_id == user_id))
    codes = [secrets.token_hex(16) for _ in range(10)]
    db.add_all(MFARecoveryCode(user_id=user_id, code_hash=digest(code)) for code in codes)
    return codes


def consume(db: Session, user_id: int, code: str) -> bool:
    normalized = code.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{32}", normalized):
        return False
    result = db.execute(update(MFARecoveryCode).where(
        MFARecoveryCode.user_id == user_id, MFARecoveryCode.code_hash == digest(normalized),
        MFARecoveryCode.consumed_at.is_(None),
    ).values(consumed_at=datetime.now(UTC)))
    return result.rowcount == 1
