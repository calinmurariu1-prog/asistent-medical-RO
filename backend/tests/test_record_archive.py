import hashlib
import io
import json
from zipfile import ZipFile

from sqlalchemy import select

from app.models.document import Document
from app.services import record_archive

API = "/api/v1"


def auth(client, email):
    credentials = {"email": email, "password": "Testing-pass-123!"}
    client.post(f"{API}/auth/register", json=credentials)
    token = client.post(f"{API}/auth/login", json=credentials).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def upload(client, headers):
    return client.post(f"{API}/documents", headers=headers, files={
        "file": ("../../private.pdf", b"%PDF-1.4 synthetic", "application/pdf")}).json()


def test_archive_is_owner_scoped_and_preserves_original_bytes(client):
    owner = auth(client, "archive-owner@example.com")
    other = auth(client, "archive-other@example.com")
    document = upload(client, owner)
    response = client.get(f"{API}/gdpr/export/archive", headers=owner)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    with ZipFile(io.BytesIO(response.content)) as archive:
        data = json.loads(archive.read("dosar.json"))
        item = data["originals_manifest"][0]
        assert item["path"] == f"originals/document-{document['id']}.pdf"
        assert archive.read(item["path"]) == b"%PDF-1.4 synthetic"
        assert item["sha256"] == hashlib.sha256(b"%PDF-1.4 synthetic").hexdigest()
        assert data["export_metadata"]["original_files_included"] is True
        assert "original_file_bytes" not in data["export_metadata"]["not_included"]
        assert len(archive.namelist()) == 2
        assert all(".." not in name for name in archive.namelist())
    response = client.get(f"{API}/gdpr/export/archive", headers=other)
    with ZipFile(io.BytesIO(response.content)) as archive:
        data = json.loads(archive.read("dosar.json"))
        assert archive.namelist() == ["dosar.json"]
        assert data["originals_manifest"] == []
        assert data["account"]["email"] == "archive-other@example.com"
    assert client.get(f"{API}/gdpr/export/archive").status_code == 401


def test_archive_missing_original_returns_no_partial_output(client, storage, monkeypatch):
    headers = auth(client, "archive-missing@example.com")
    upload(client, headers)

    def missing(key):
        raise FileNotFoundError("private-storage-key")

    monkeypatch.setattr(storage, "get", missing)
    response = client.get(f"{API}/gdpr/export/archive", headers=headers)
    assert response.status_code == 503
    assert "private-storage-key" not in response.text
    assert response.headers["content-type"].startswith("application/json")


def test_archive_checks_actual_size_not_just_database_metadata(client, db_session, monkeypatch):
    headers = auth(client, "archive-limit@example.com")
    upload(client, headers)
    document = db_session.scalar(select(Document))
    document.size_bytes = 0
    db_session.commit()
    monkeypatch.setattr(record_archive, "MAX_BYTES", 5)
    response = client.get(f"{API}/gdpr/export/archive", headers=headers)
    assert response.status_code == 413
