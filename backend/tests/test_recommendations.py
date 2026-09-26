"""Tests for Module 7 - Orientative recommendations."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="rec@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_empty_record_has_disclaimer_only(client):
    h = _auth(client)
    body = client.get(f"{API}/recommendations", headers=h).json()
    assert body["questions_for_doctor"] == []
    assert body["alerts"] == []
    assert "orientative" in body["disclaimer"].lower()


def test_abnormal_lab_generates_recommendations(client):
    h = _auth(client)
    # An out-of-range value is not automatically a clinical emergency.
    client.post(
        f"{API}/labs",
        headers=h,
        json={"analyte": "Glicemie", "value": 200, "unit": "mg/dL",
              "ref_low": 70, "ref_high": 99, "measured_on": "2026-01-10"},
    )
    body = client.get(f"{API}/recommendations", headers=h).json()
    assert any("Glicemie" in q for q in body["questions_for_doctor"])
    assert body["alerts"] == []
    assert body["lifestyle"]                                   # metabolic -> lifestyle
    assert any("Glicemie" in m for m in body["monitoring"])


def test_medication_interaction_generates_question(client):
    h = _auth(client)
    client.post(f"{API}/medications", headers=h,
                json={"name": "Sintrom", "active_substance": "warfarina"})
    client.post(f"{API}/medications", headers=h,
                json={"name": "Aspenter", "active_substance": "aspirina"})
    body = client.get(f"{API}/recommendations", headers=h).json()
    assert any("interacțiune" in q.lower() for q in body["questions_for_doctor"])
