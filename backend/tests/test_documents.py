"""Tests for Module 4 - Documents, OCR pipeline and AI extraction (mock)."""
from __future__ import annotations

import io

API = "/api/v1"

SAMPLE_LAB_TEXT = (
    "Buletin de analize\n"
    "Glicemie 105 mg/dL (70 - 99)\n"
    "Hemoglobina: 13.5 g/dL 12 - 16\n"
    "Colesterol total 260 mg/dL (0 - 200)\n"
    "Diagnostic: sindrom metabolic\n"
)


def _auth_headers(client, email="doc@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _upload(client, headers, content=SAMPLE_LAB_TEXT, filename="analize.pdf",
            content_type="application/pdf", category="lab"):
    return client.post(
        f"{API}/documents",
        headers=headers,
        files={"file": (filename, io.BytesIO(content.encode()), content_type)},
        data={"category": category},
    )


def test_upload_rejects_unsupported_type(client):
    h = _auth_headers(client)
    r = _upload(client, h, filename="note.txt", content_type="text/plain")
    assert r.status_code == 415


def test_upload_rejects_empty_file(client):
    h = _auth_headers(client)
    r = _upload(client, h, content="")
    assert r.status_code == 400


def test_upload_processes_and_extracts_lab_values(client):
    """A PDF with embedded text is parsed by pypdf; the mock AI extracts labs."""
    h = _auth_headers(client)
    # Build a real one-page PDF containing the sample text so pypdf can read it.
    pdf_bytes = _make_text_pdf(SAMPLE_LAB_TEXT)
    r = client.post(
        f"{API}/documents",
        headers=h,
        files={"file": ("analize.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"category": "lab"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "done"
    analytes = {lr["analyte"]: lr for lr in body["lab_results"]}
    assert "Glicemie" in analytes
    assert analytes["Glicemie"]["value"] == 105.0
    assert analytes["Glicemie"]["flag"] == "high"  # 105 > 99, within 0.5*span
    # 260 vs (0-200): 0.5*span = 100, 260 < 300 -> high (not critical)
    assert analytes["Colesterol total"]["flag"] == "high"


def test_list_filter_get_and_delete(client):
    h = _auth_headers(client)
    up = _upload(client, h)
    assert up.status_code == 201
    doc_id = up.json()["id"]

    # List + category filter
    assert len(client.get(f"{API}/documents", headers=h).json()) == 1
    assert len(client.get(f"{API}/documents?category=lab", headers=h).json()) == 1
    assert client.get(f"{API}/documents?category=ct", headers=h).json() == []

    # Detail
    assert client.get(f"{API}/documents/{doc_id}", headers=h).json()["id"] == doc_id

    # Download presigned URL
    dl = client.get(f"{API}/documents/{doc_id}/download", headers=h).json()
    assert dl["url"].startswith("https://storage.test/")

    # Delete
    assert client.delete(f"{API}/documents/{doc_id}", headers=h).status_code == 204
    assert client.get(f"{API}/documents/{doc_id}", headers=h).status_code == 404


def test_documents_are_isolated_per_patient(client):
    h1 = _auth_headers(client, "p1@example.com")
    h2 = _auth_headers(client, "p2@example.com")
    doc_id = _upload(client, h1).json()["id"]
    # Patient 2 cannot see or fetch patient 1's document.
    assert client.get(f"{API}/documents", headers=h2).json() == []
    assert client.get(f"{API}/documents/{doc_id}", headers=h2).status_code == 404


def _make_text_pdf(text: str) -> bytes:
    """Minimal single-page PDF with a text stream (readable by pypdf)."""
    from pypdf import PdfWriter
    from pypdf.generic import (
        ArrayObject,
        DecodedStreamObject,
        DictionaryObject,
        FloatObject,
        NameObject,
        NumberObject,
    )

    lines = text.splitlines()
    content = "BT /F1 12 Tf 40 800 Td 14 TL " + " ".join(
        f"({line.replace('(', '').replace(')', '')}) Tj T*" for line in lines
    ) + " ET"

    writer = PdfWriter()
    writer.add_blank_page(width=595, height=842)
    page = writer.pages[0]

    stream = DecodedStreamObject()
    stream.set_data(content.encode("latin-1"))
    stream_ref = writer._add_object(stream)
    page[NameObject("/Contents")] = stream_ref

    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font_ref = writer._add_object(font)
    resources = DictionaryObject()
    fonts = DictionaryObject()
    fonts[NameObject("/F1")] = font_ref
    resources[NameObject("/Font")] = fonts
    page[NameObject("/Resources")] = resources
    page[NameObject("/MediaBox")] = ArrayObject(
        [NumberObject(0), NumberObject(0), FloatObject(595), FloatObject(842)]
    )

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def test_original_endpoint_checks_owner(client):
    owner = _auth_headers(client, "owner-original@example.com")
    other = _auth_headers(client, "other-original@example.com")
    data = _make_text_pdf(SAMPLE_LAB_TEXT)
    result = client.post(API + "/documents", headers=owner,
                         files={"file": ("original.pdf", data, "application/pdf")})
    assert result.status_code == 201
    url = API + f"/documents/{result.json()['id']}/original"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=other).status_code == 404
    downloaded = client.get(url, headers=owner)
    assert downloaded.status_code == 200
    assert downloaded.content == data
    assert downloaded.headers["cache-control"] == "no-store"


def test_upload_limit_reads_only_bounded_bytes(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.documents.MAX_SIZE_BYTES", 10)
    headers = _auth_headers(client, "limit-original@example.com")
    assert client.post(API + "/documents", headers=headers,
                       files={"file": ("big.pdf", b"x" * 11, "application/pdf")}
                       ).status_code == 413
