"""Helper for writing audit-log entries (security & GDPR accountability)."""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.user import AuditLog


def record(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    detail: str | None = None,
) -> None:
    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id is not None else None,
        ip_address=ip_address,
        user_agent=user_agent,
        detail=detail,
        created_at=datetime.now(UTC),
    )
    db.add(entry)
    db.commit()
