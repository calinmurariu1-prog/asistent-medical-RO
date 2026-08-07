"""Tests for GDPR endpoints: export, consent, account deletion."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="gdpr@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_export_contains_account_and_records(client):
    h = _auth(client)
    client.post(f"{API}/labs", headers=h, json={
        "analyte": "Glicemie", "value": 90, "unit": "mg/dL", "measured_on": "2026-01-10"})
    client.post(f"{API}/medications", headers=h, json={"name": "Metformin"})

    data = client.get(f"{API}/gdpr/export", headers=h).json()
    assert data["account"]["email"] == "gdpr@example.com"
    assert data["lab_results"][0]["analyte"] == "Glicemie"
    assert data["medications"][0]["name"] == "Metformin"


def test_consent_grant_and_revoke(client):
    h = _auth(client)
    r = client.post(f"{API}/gdpr/consents", headers=h,
                    json={"consent_type": "ai_processing", "granted": True})
    assert r.status_code == 201
    consents = client.get(f"{API}/gdpr/consents", headers=h).json()
    assert consents[0]["granted"] is True

    client.post(f"{API}/gdpr/consents", headers=h,
                json={"consent_type": "ai_processing", "granted": False})
    latest = client.get(f"{API}/gdpr/consents", headers=h).json()
    ai = next(c for c in latest if c["consent_type"] == "ai_processing")
    assert ai["granted"] is False  # latest state wins


def test_delete_account_requires_password_and_confirm(client):
    h = _auth(client)
    assert client.request(
        "POST", f"{API}/gdpr/delete-account", headers=h,
        json={"password": "Parola1234", "confirm": False}).status_code == 400
    assert client.request(
        "POST", f"{API}/gdpr/delete-account", headers=h,
        json={"password": "gresit", "confirm": True}).status_code == 401


def test_delete_account_erases_user(client):
    h = _auth(client)
    r = client.request(
        "POST", f"{API}/gdpr/delete-account", headers=h,
        json={"password": "Parola1234", "confirm": True})
    assert r.status_code == 204
    # Token no longer resolves to a user.
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401
