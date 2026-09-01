"""Teste pentru autentificare, documente salvate și export."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _token(email: str = "user@example.com", password: str = "parola123") -> str:
    r = client.post("/auth/register", json={"email": email, "password": password})
    if r.status_code == 409:  # deja înregistrat -> login
        r = client.post("/auth/login", data={"username": email, "password": password})
    return r.json()["access_token"]


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_register_and_me():
    token = _token("me@example.com")
    r = client.get("/auth/me", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["email"] == "me@example.com"


def test_login_wrong_password():
    _token("wp@example.com", "corect1")
    r = client.post("/auth/login", data={"username": "wp@example.com", "password": "gresit9"})
    assert r.status_code == 401


def test_documents_require_auth():
    assert client.get("/documents").status_code == 401


def test_document_crud_and_isolation():
    token = _token("owner@example.com")
    r = client.post(
        "/documents",
        headers=_auth(token),
        json={"title": "Contract test", "category": "juridic", "content": "Conținut ș ț ă."},
    )
    assert r.status_code == 201
    doc_id = r.json()["id"]

    r = client.get("/documents", headers=_auth(token))
    assert any(d["id"] == doc_id for d in r.json())

    # Alt utilizator nu are acces.
    other = _token("other@example.com")
    assert client.get(f"/documents/{doc_id}", headers=_auth(other)).status_code == 404

    assert client.delete(f"/documents/{doc_id}", headers=_auth(token)).status_code == 204
    assert client.get(f"/documents/{doc_id}", headers=_auth(token)).status_code == 404


def test_export_pdf_and_docx():
    token = _token("exp@example.com")
    r = client.post(
        "/documents",
        headers=_auth(token),
        json={"title": "Contract prestări", "content": "Text cu diacritice: ș ț ă â î."},
    )
    doc_id = r.json()["id"]

    r_pdf = client.get(f"/documents/{doc_id}/export?format=pdf", headers=_auth(token))
    assert r_pdf.status_code == 200
    assert r_pdf.content[:4] == b"%PDF"

    r_docx = client.get(f"/documents/{doc_id}/export?format=docx", headers=_auth(token))
    assert r_docx.status_code == 200
    assert r_docx.content[:2] == b"PK"  # zip/docx


def test_inline_export():
    token = _token("inl@example.com")
    r = client.post(
        "/export",
        headers=_auth(token),
        json={"title": "Raport", "content": "Conținut export direct.", "format": "pdf"},
    )
    assert r.status_code == 200
    assert r.content[:4] == b"%PDF"
