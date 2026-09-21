"""Failed uploads retain durable encrypted cleanup intent, never delete saved originals."""
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select, update

from app.core.config import settings
from app.core.security import decrypt_field
from app.models.document import Document
from app.models.storage_deletion import StorageDeletion
from app.services import storage_cleanup
from app.services.storage import LocalStorage
from tests.test_storage_cleanup import API, auth


def send(client, headers):
    data = (Path(__file__).parents[2] / "demo/analize-fictive.pdf").read_bytes()
    return client.post(f"{API}/documents", headers=headers,
                       files={"file": ("fictitious.pdf", data, "application/pdf")})


def expire(db):
    db.execute(update(StorageDeletion).values(
        claimed_until=datetime.now(UTC) - timedelta(seconds=1)))
    db.commit()


@pytest.mark.parametrize("failure", ["storage", "database", "uncertain_commit"])
def test_upload_failure_compensation(client, db_session, storage, monkeypatch, failure):
    headers = auth(client, f"upload-{failure}@example.com")
    real_put, real_commit = storage.put, db_session.commit
    writes = []

    def put(key, data, content_type=None):
        # Durable intent exists before even a partial write.
        job = db_session.scalar(select(StorageDeletion))
        assert job is not None and decrypt_field(job.encrypted_key) == key
        assert key not in job.encrypted_key
        real_put(key, data, content_type)
        writes.append(key)
        if failure == "storage":
            raise OSError("private storage detail must not appear")

    def commit():
        if writes:
            if failure == "uncertain_commit":
                real_commit()
            raise OSError("private database detail must not appear")
        real_commit()

    with monkeypatch.context() as patch:
        patch.setattr(storage, "put", put)
        if failure != "storage":
            patch.setattr(db_session, "commit", commit)
        response = send(client, headers)
    assert response.status_code == 503
    assert "private" not in response.text
    assert len(storage._objects) == 1
    if failure == "uncertain_commit":
        assert db_session.scalar(select(Document)) is not None
        assert db_session.scalar(select(StorageDeletion)) is None
        assert storage_cleanup.process_pending(db_session, storage) == 0
        assert len(storage._objects) == 1
    else:
        assert db_session.scalar(select(Document)) is None
        assert db_session.scalar(select(StorageDeletion)) is not None
        assert storage_cleanup.process_pending(db_session, storage) == 0
        expire(db_session)
        assert storage_cleanup.process_pending(db_session, storage) == 1
        assert storage._objects == {}


def test_successful_upload_cancels_compensation(client, db_session, storage):
    headers = auth(client, "upload-success@example.com")
    response = send(client, headers)
    assert response.status_code == 201
    assert db_session.scalar(select(StorageDeletion)) is None
    assert storage_cleanup.process_pending(db_session, storage) == 0
    assert client.get(f"{API}/documents/{response.json()['id']}/original",
                      headers=headers).status_code == 200


def test_cleanup_removes_interrupted_local_temporary_file(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_DATA_DIR", str(tmp_path))
    local = LocalStorage()
    temporary = local._path("unique-object").with_suffix(".tmp")
    temporary.write_bytes(b"fictitious interrupted ciphertext")
    local.delete("unique-object")
    assert not temporary.exists()
    local.delete("unique-object")  # Idempotent after process restart.


def test_intent_commit_failure_never_writes_original(client, db_session, storage, monkeypatch):
    headers = auth(client, "upload-intent-failure@example.com")
    real_commit = db_session.commit
    with monkeypatch.context() as patch:
        def fail():
            if db_session.scalar(select(StorageDeletion)) is not None:
                raise OSError("database unavailable")
            real_commit()
        patch.setattr(db_session, "commit", fail)
        assert send(client, headers).status_code == 503
    db_session.rollback()
    assert storage._objects == {}
    assert db_session.scalar(select(Document)) is None
