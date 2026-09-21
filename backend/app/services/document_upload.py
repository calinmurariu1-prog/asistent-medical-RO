"""Durable compensation for originals whose document transaction never commits."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.storage_deletion import StorageDeletion
from app.services import storage_cleanup
from app.services.storage import Storage


def persist(db: Session, storage: Storage, document: Document, data: bytes) -> None:
    # Commit cleanup intent BEFORE any external write. A terminated process leaves
    # this intent available after ten minutes, including partial storage writes.
    deadline = datetime.now(UTC) + timedelta(minutes=10)
    job_id = storage_cleanup.enqueue(db, [document.storage_key])[0]
    db.flush()
    db.execute(update(StorageDeletion).where(StorageDeletion.id == job_id).values(
        claimed_until=deadline))
    db.commit()
    try:
        # Hold the same row lock used by cleanup until document + intent removal
        # commit atomically. Expired/lost reservations never start a storage write.
        locked = db.execute(update(StorageDeletion).where(
            StorageDeletion.id == job_id,
            StorageDeletion.claimed_until == deadline,
            StorageDeletion.claimed_until > datetime.now(UTC),
        ).values(claimed_until=deadline))
        if locked.rowcount != 1:
            raise RuntimeError("upload_reservation_expired")
        storage.put(document.storage_key, data, document.content_type)
        db.add(document)
        db.execute(delete(StorageDeletion).where(StorageDeletion.id == job_id))
        db.commit()
    except BaseException:
        # Never remove intent on an uncertain commit outcome. If the commit did
        # succeed, its intent is already gone; otherwise the worker will retry.
        db.rollback()
        raise
