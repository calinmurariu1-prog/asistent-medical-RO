"""Tests for Module 2 - Patient profile."""
from __future__ import annotations

API = "/api/v1"


def _auth_headers(client):
    client.post(
        f"{API}/auth/register",
        json={"email": "b@example.com", "password": "Parola1234"},
    )
    tokens = client.post(
        f"{API}/auth/login",
        json={"email": "b@example.com", "password": "Parola1234"},
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_update_profile_and_bmi(client):
    h = _auth_headers(client)
    r = client.put(
        f"{API}/patients/me",
        headers=h,
        json={"first_name": "Ion", "weight_kg": 80, "height_cm": 180, "sex": "male"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["first_name"] == "Ion"
    assert body["bmi"] == 24.7  # 80 / 1.8^2


def test_allergies_crud(client):
    h = _auth_headers(client)
    r = client.post(
        f"{API}/patients/me/allergies",
        headers=h,
        json={"substance": "Penicilina", "severity": "severe"},
    )
    assert r.status_code == 201, r.text
    allergy_id = r.json()["id"]

    r = client.get(f"{API}/patients/me/allergies", headers=h)
    assert len(r.json()) == 1

    r = client.delete(f"{API}/patients/me/allergies/{allergy_id}", headers=h)
    assert r.status_code == 204
    assert client.get(f"{API}/patients/me/allergies", headers=h).json() == []
