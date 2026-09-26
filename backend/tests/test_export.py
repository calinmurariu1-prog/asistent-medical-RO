"""Tests for Module 13 - Report export (PDF / Word)."""

from __future__ import annotations

API = "/api/v1"


def _auth(client, email="exp@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _seed(client, h):
    client.put(
        f"{API}/patients/me",
        headers=h,
        json={"first_name": "Ion", "last_name": "Pop", "weight_kg": 80, "height_cm": 180},
    )
    client.post(
        f"{API}/labs",
        headers=h,
        json={
            "analyte": "Glicemie",
            "value": 200,
            "unit": "mg/dL",
            "ref_low": 70,
            "ref_high": 99,
            "measured_on": "2026-01-10",
        },
    )
    client.post(
        f"{API}/medications",
        headers=h,
        json={"name": "Metformin", "dose": "500mg", "frequency": "2x/zi"},
    )


def test_export_pdf(client):
    h = _auth(client)
    _seed(client, h)
    r = client.get(f"{API}/export/report.pdf", headers=h)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/pdf"
    assert r.content[:5] == b"%PDF-"
    assert "attachment" in r.headers["content-disposition"]


def test_export_docx(client):
    h = _auth(client)
    _seed(client, h)
    r = client.get(f"{API}/export/report.docx", headers=h)
    assert r.status_code == 200, r.text
    assert "wordprocessingml" in r.headers["content-type"]
    assert r.content[:2] == b"PK"  # docx is a zip archive


def test_export_complete_content_unicode_and_account_isolation(client):
    import io

    from docx import Document
    from pypdf import PdfReader

    h = _auth(client)
    _seed(client, h)
    client.post(
        f"{API}/labs",
        headers=h,
        json={
            "analyte": "Glicemie",
            "value": 91,
            "unit": "mg/dL",
            "ref_low": 70,
            "ref_high": 99,
            "measured_on": "2025-01-10",
        },
    )
    assert (
        client.post(
            f"{API}/history",
            headers=h,
            json={
                "event_type": "observation",
                "title": "Observație fictivă <test>",
                "description": "Detalii Ștefan & Țincă, fără interpretare medicală.",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"{API}/patients/me/allergies",
            headers=h,
            json={
                "substance": "Alergen fictiv",
                "reaction": "Reacție fictivă",
                "severity": "unknown",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"{API}/history/vaccines",
            headers=h,
            json={"name": "Vaccin fictiv", "dose": "Doză fictivă", "administered_on": "2025-02-01"},
        ).status_code
        == 201
    )
    expected = (
        "Alergen fictiv",
        "Vaccin fictiv",
        "Detalii Ștefan & Țincă",
        "2025-01-10",
        "2026-01-10",
        "<test>",
    )
    pdf = client.get(f"{API}/export/report.pdf", headers=h)
    assert pdf.status_code == 200
    text = " ".join(page.extract_text() for page in PdfReader(io.BytesIO(pdf.content)).pages)
    for fragment in expected:
        assert fragment in text
    docx = Document(io.BytesIO(client.get(f"{API}/export/report.docx", headers=h).content))
    word_text = " ".join(
        cell.text for table in docx.tables for row in table.rows for cell in row.cells
    )
    for fragment in expected:
        assert fragment in word_text
    other = _auth(client, "export-other@example.com")
    other_pdf = client.get(f"{API}/export/report.pdf", headers=other)
    other_text = " ".join(
        page.extract_text() for page in PdfReader(io.BytesIO(other_pdf.content)).pages
    )
    assert "Alergen fictiv" not in other_text
    assert "Ștefan" not in other_text


def test_pdf_long_history_wraps_across_pages():
    import io

    from pypdf import PdfReader

    from app.services.report import render_pdf

    data = {
        "generated_at": "Test fictiv",
        "patient": {
            "name": "Ștefan <img src='file:///private'> & Țincă",
            "birth_date": "-",
            "sex": "-",
            "blood_type": "-",
            "bmi": None,
        },
        "history": [
            {
                "date": "-",
                "type": "observation",
                "title": "Text lung",
                "description": "Descriere fictivă foarte lungă. " * 400,
            }
        ],
        "labs": [],
        "medications": [],
        "recommendations": {"alerts": [], "questions_for_doctor": []},
    }
    pdf = render_pdf(data)
    pages = PdfReader(io.BytesIO(pdf)).pages
    assert len(pages) > 1
    text = " ".join(page.extract_text() for page in pages)
    assert "file:///private" in text
    assert "Descriere fictivă" in text
