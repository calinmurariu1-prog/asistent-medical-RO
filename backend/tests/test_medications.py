"""Tests for Module 9 - Medications and interaction/duplicate checks."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="med@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _add(client, h, name, substance=None, active=True):
    return client.post(
        f"{API}/medications",
        headers=h,
        json={"name": name, "active_substance": substance, "is_active": active},
    )


def test_crud(client):
    h = _auth(client)
    r = _add(client, h, "Nurofen", "ibuprofen")
    assert r.status_code == 201
    med_id = r.json()["id"]

    assert len(client.get(f"{API}/medications", headers=h).json()) == 1

    r = client.patch(f"{API}/medications/{med_id}", headers=h, json={"is_active": False})
    assert r.json()["is_active"] is False
    assert client.get(f"{API}/medications?active_only=true", headers=h).json() == []

    assert client.delete(f"{API}/medications/{med_id}", headers=h).status_code == 204


def test_interaction_detected(client):
    h = _auth(client)
    _add(client, h, "Sintrom", "warfarina")
    _add(client, h, "Aspenter", "aspirina")
    body = client.get(f"{API}/medications/check", headers=h).json()
    assert len(body["interactions"]) == 1
    assert body["interactions"][0]["severity"] == "severe"
    assert "NU înlocuiește" in body["disclaimer"]


def test_duplicate_detected(client):
    h = _auth(client)
    _add(client, h, "Nurofen", "ibuprofen")
    _add(client, h, "Ibumax", "ibuprofen")
    body = client.get(f"{API}/medications/check", headers=h).json()
    assert len(body["duplicates"]) == 1
    assert set(body["duplicates"][0]["medications"]) == {"Nurofen", "Ibumax"}


def test_inactive_meds_excluded_from_check(client):
    h = _auth(client)
    _add(client, h, "Sintrom", "warfarina")
    _add(client, h, "Aspenter", "aspirina", active=False)
    body = client.get(f"{API}/medications/check", headers=h).json()
    assert body["interactions"] == []
