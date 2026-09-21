"""Storage erasure is owner-scoped, persistent and retryable."""
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.storage_deletion import StorageDeletion
from app.services import storage_cleanup
from app.services.storage import LocalStorage

API = "/api/v1"


def auth(client, email):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    token = client.post(f"{API}/auth/login", json={
        "email": email, "password": "Parola1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload(client, h):
    fixture = Path(__file__).parents[2] / "demo/analize-fictive.pdf"
    return client.post(f"{API}/documents", headers=h,
                       files={"file": ("fictiv.pdf", fixture.read_bytes(), "application/pdf")}
                       ).json()


def test_account_erasure_is_owner_scoped(client, db_session, storage):
    from app.models.user import RecoveryToken

    h = auth(client, "erase@example.com")
    other = auth(client, "keep@example.com")
    original = upload(client, h)
    kept = upload(client, other)
    assert len(storage._objects) == 2
    response = client.post(f"{API}/gdpr/delete-account", headers=h,
                           json={"password": "Parola1234", "confirm": True})
    assert response.status_code == 204
    assert len(storage._objects) == 1
    assert client.get(f"{API}/documents/{original['id']}/original", headers=h).status_code == 401
    assert client.get(f"{API}/documents/{kept['id']}/original", headers=other).status_code == 200
    assert not list(db_session.scalars(select(StorageDeletion)))
    tokens = list(db_session.scalars(select(RecoveryToken)))
    assert len(tokens) == 1  # Only the other account's verification token.
    messages = [p.read_text(encoding="utf-8") for p in
                (Path(settings.LOCAL_DATA_DIR) / "mailbox").glob("*.txt")]
    assert not any("To: erase@example.com\n" in m for m in messages)
    assert any("To: keep@example.com\n" in m for m in messages)


def test_failed_original_deletion_is_pending_and_retried(client, db_session, storage, monkeypatch):
    h = auth(client, "pending@example.com")
    upload(client, h)
    real_delete = storage.delete

    def fail(_key):
        raise OSError("simulated storage failure")

    monkeypatch.setattr(storage, "delete", fail)
    response = client.post(f"{API}/gdpr/delete-account", headers=h,
                           json={"password": "Parola1234", "confirm": True})
    assert response.status_code == 202
    assert response.json()["cleanup_pending"] is True
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401
    job = db_session.scalar(select(StorageDeletion))
    assert job.attempts == 1 and "fictiv.pdf" not in job.encrypted_key
    monkeypatch.setattr(storage, "delete", real_delete)
    storage_cleanup.process_pending(db_session, storage)
    assert not storage._objects
    assert not list(db_session.scalars(select(StorageDeletion)))


def test_document_deletion_does_not_drop_failed_cleanup(client, db_session, storage, monkeypatch):
    h = auth(client, "single@example.com")
    other = auth(client, "single-other@example.com")
    document = upload(client, h)
    assert client.delete(f"{API}/documents/{document['id']}", headers=other).status_code == 404
    def fail(_key):
        raise OSError("offline")
    monkeypatch.setattr(storage, "delete", fail)
    response = client.delete(f"{API}/documents/{document['id']}", headers=h)
    assert response.status_code == 202
    assert client.get(f"{API}/documents", headers=h).json() == []
    assert db_session.scalar(select(StorageDeletion)) is not None


def test_cleanup_intent_survives_database_reopen(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    monkeypatch.setattr(settings, "LOCAL_DATA_DIR", str(tmp_path / "private"))
    storage = LocalStorage()
    storage.put("fictitious-key", b"original")
    url = f"sqlite:///{(tmp_path / 'cleanup.db').as_posix()}"
    engine = create_engine(url)
    StorageDeletion.__table__.create(engine)
    with Session(engine) as db:
        ids = storage_cleanup.enqueue(db, ["fictitious-key"])
        db.commit()
    engine.dispose()
    reopened = create_engine(url)
    with Session(reopened) as db:
        assert storage_cleanup.pending_count(db, ids) == 1
        assert storage_cleanup.process_pending(db, storage) == 1
        assert storage_cleanup.pending_count(db, ids) == 0
    assert list(storage.root.iterdir()) == []
    reopened.dispose()


def test_cleanup_claim_blocks_duplicate_work_and_expired_claim_recovers(tmp_path, monkeypatch):
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    monkeypatch.setattr(settings, "STORAGE_BACKEND", "local")
    engine = create_engine(f"sqlite:///{(tmp_path / 'leased.db').as_posix()}")
    StorageDeletion.__table__.create(engine)
    calls = []

    class PausedStorage:
        def delete(self, key):
            calls.append(key)
            with Session(engine) as competing:
                assert storage_cleanup.process_pending(competing, self) == 0

    with Session(engine) as db:
        ids = storage_cleanup.enqueue(db, ["one"])
        db.commit()
        assert storage_cleanup.process_pending(db, PausedStorage()) == 1
        ids = storage_cleanup.enqueue(db, ["two"])
        db.commit()
        db.execute(update(StorageDeletion).where(StorageDeletion.id.in_(ids)).values(
            claimed_until=datetime.now(UTC) + timedelta(minutes=2)))
        db.commit()
        assert storage_cleanup.process_pending(db, PausedStorage()) == 0
        db.execute(update(StorageDeletion).where(StorageDeletion.id.in_(ids)).values(
            claimed_until=datetime.now(UTC) - timedelta(seconds=1)))
        db.commit()
        assert storage_cleanup.process_pending(db, PausedStorage()) == 1
    assert calls == ["one", "two"]
    engine.dispose()


def test_local_mail_erasure_includes_interrupted_temporary_messages(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "LOCAL_DATA_DIR", str(tmp_path))
    mailbox = tmp_path / "mailbox"
    mailbox.mkdir()
    owned = mailbox / "interrupted.tmp"
    owned.write_text("To: owner@example.com\nSubject: Test\n\nprivate-token", encoding="utf-8")
    other = mailbox / "other.tmp"
    other.write_text("To: other@example.com\nSubject: Test", encoding="utf-8")
    storage_cleanup.delete_local_mail("owner@example.com")
    assert not owned.exists()
    assert other.exists()
