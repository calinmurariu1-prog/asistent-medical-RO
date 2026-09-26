"""Module 15 - Admin panel (users, stats, audit logs, feedback)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_admin
from app.core.config import settings
from app.core.database import get_db
from app.models.chat import AIChat
from app.models.document import Document, LabResult
from app.models.feedback import Feedback
from app.models.patient import Patient
from app.models.storage_deletion import StorageDeletion
from app.models.user import AuditLog, User
from app.schemas.admin import (
    AdminStats,
    AdminUserOut,
    AdminUserUpdate,
    AuditLogOut,
    FeedbackOut,
)

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _count(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


@router.get("/stats", response_model=AdminStats)
def stats(db: Session = Depends(get_db)) -> AdminStats:
    return AdminStats(
        users=_count(db, User),
        patients=_count(db, Patient),
        documents=_count(db, Document),
        lab_results=_count(db, LabResult),
        chats=_count(db, AIChat),
        feedback=_count(db, Feedback),
    )


@router.get("/users", response_model=list[AdminUserOut])
def list_users(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[User]:
    stmt = select(User).order_by(User.id).limit(limit).offset(offset)
    return list(db.scalars(stmt).all())


@router.patch("/users/{user_id}", response_model=AdminUserOut)
def update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilizator inexistent")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/audit-logs", response_model=list[AuditLogOut])
def audit_logs(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/feedback", response_model=list[FeedbackOut])
def list_feedback(
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[Feedback]:
    stmt = select(Feedback).order_by(Feedback.created_at.desc()).limit(limit)
    return list(db.scalars(stmt).all())


@router.get("/storage-cleanup")
def storage_cleanup_status(db: Session = Depends(get_db)) -> dict:
    return {
        "pending": _count(db, StorageDeletion),
        "oldest_pending": db.scalar(select(func.min(StorageDeletion.created_at))),
        "worker_enabled": settings.STORAGE_CLEANUP_ENABLED,
        "retry_interval_seconds": settings.STORAGE_CLEANUP_INTERVAL_SECONDS,
    }
