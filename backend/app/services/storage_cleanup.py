"""Retryable original-file cleanup; intent and DB erasure commit atomically."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import decrypt_field, encrypt_field
from app.models.storage_deletion import StorageDeletion
from app.services.storage import Storage, get_storage

logger = logging.getLogger(__name__)


def enqueue(db: Session, keys: list[str], backend: str | None = None) -> list[str]:
    ids = []
    for key in set(keys):
        job_id = uuid.uuid4().hex
        db.add(StorageDeletion(id=job_id, encrypted_key=encrypt_field(key),
                               backend=backend or settings.STORAGE_BACKEND))
        ids.append(job_id)
    return ids


def delete_local_mail(email: str) -> None:
    root = (Path(settings.LOCAL_DATA_DIR) / "mailbox").resolve()
    if not root.exists():
        return
    for path in root.glob("*.txt"):
        if path.is_symlink() or path.resolve().parent != root:
            continue
        try:
            with path.open(encoding="utf-8") as message:
                recipient = message.readline().strip()
        except FileNotFoundError:
            continue
        if recipient == f"To: {email}":
            path.unlink(missing_ok=True)


def process_pending(db: Session, storage: Storage | None, ids: list[str] | None = None) -> int:
    now = datetime.now(UTC)
    available = or_(StorageDeletion.claimed_until.is_(None), StorageDeletion.claimed_until < now)
    statement = select(StorageDeletion).where(available,
        StorageDeletion.backend.in_([settings.STORAGE_BACKEND, "mailbox"])
    ).order_by(StorageDeletion.last_attempt_at.asc().nulls_first(), StorageDeletion.created_at)
    if ids is not None:
        statement = statement.where(StorageDeletion.id.in_(ids))
    jobs = list(db.scalars(statement.limit(100)))
    completed = 0
    for job in jobs:
        attempt_time = datetime.now(UTC)
        claim_available = or_(StorageDeletion.claimed_until.is_(None),
                              StorageDeletion.claimed_until < attempt_time)
        claimed = db.execute(update(StorageDeletion).where(
            StorageDeletion.id == job.id, claim_available,
        ).values(claimed_until=attempt_time + timedelta(minutes=2)),
            execution_options={"synchronize_session": False})
        db.commit()
        if claimed.rowcount != 1:
            continue
        try:
            key = decrypt_field(job.encrypted_key)
            if not key:
                raise ValueError("cleanup_key_unavailable")
            if job.backend == "mailbox":
                delete_local_mail(key)
            else:
                (storage or get_storage()).delete(key)  # Keys are never reused.
        except Exception as exc:  # noqa: BLE001
            logger.warning("Storage cleanup deferred (%s)", type(exc).__name__)
            db.execute(update(StorageDeletion).where(StorageDeletion.id == job.id).values(
                claimed_until=None), execution_options={"synchronize_session": False})
            job.attempts += 1
            job.last_attempt_at = datetime.now(UTC)
        else:
            db.delete(job)
            completed += 1
        db.commit()
    return completed


def run_batch() -> None:
    from app.services.token_service import purge_expired

    with SessionLocal() as db:
        purge_expired(db)
        exists = db.scalar(select(StorageDeletion.id).where(
            StorageDeletion.backend.in_([settings.STORAGE_BACKEND, "mailbox"])).limit(1))
        if exists:
            process_pending(db, None)


async def worker(stop: asyncio.Event) -> None:
    while not stop.is_set():
        try:
            await asyncio.to_thread(run_batch)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Storage cleanup worker deferred (%s)", type(exc).__name__)
        try:
            await asyncio.wait_for(stop.wait(), timeout=settings.STORAGE_CLEANUP_INTERVAL_SECONDS)
        except TimeoutError:
            pass


def pending_count(db: Session, ids: list[str]) -> int:
    return db.scalar(select(func.count()).select_from(StorageDeletion).where(
        StorageDeletion.id.in_(ids))) or 0
