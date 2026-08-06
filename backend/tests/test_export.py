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
    client.put(f"{API}/patients/me", headers=h,
               json={"first_name": "Ion", "last_name": "Pop", "weight_kg": 80,
                     "height_cm": 180})
    client.post(f"{API}/labs", headers=h, json={
        "analyte": "Glicemie", "value": 200, "unit": "mg/dL",
        "ref_low": 70, "ref_high": 99, "measured_on": "2026-01-10"})
    client.post(f"{API}/medications", headers=h,
                json={"name": "Metformin", "dose": "500mg", "frequency": "2x/zi"})


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
