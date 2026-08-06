"""Tests for Module 3 - Medical history & vaccines."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="hist@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _add(client, h, **kw):
    payload = {"event_type": "diagnosis", "title": "Hipertensiune"}
    payload.update(kw)
    return client.post(f"{API}/history", headers=h, json=payload)


def test_crud_and_filters(client):
    h = _auth(client)
    _add(client, h, event_date="2024-05-01", is_chronic=True)
    _add(client, h, event_type="surgery", title="Apendicectomie", event_date="2020-03-01")

    assert len(client.get(f"{API}/history", headers=h).json()) == 2
    assert len(client.get(f"{API}/history?year=2024", headers=h).json()) == 1
    assert len(client.get(f"{API}/history?event_type=surgery", headers=h).json()) == 1
    assert len(client.get(f"{API}/history?is_chronic=true", headers=h).json()) == 1


def test_update_and_delete(client):
    h = _auth(client)
    entry_id = _add(client, h).json()["id"]
    r = client.patch(f"{API}/history/{entry_id}", headers=h, json={"title": "HTA esențială"})
    assert r.json()["title"] == "HTA esențială"
    assert client.delete(f"{API}/history/{entry_id}", headers=h).status_code == 204


def test_vaccines(client):
    h = _auth(client)
    r = client.post(
        f"{API}/history/vaccines",
        headers=h,
        json={"name": "Gripal", "administered_on": "2025-10-01"},
    )
    assert r.status_code == 201
    vid = r.json()["id"]
    assert len(client.get(f"{API}/history/vaccines", headers=h).json()) == 1
    assert client.delete(f"{API}/history/vaccines/{vid}", headers=h).status_code == 204


def test_history_isolated(client):
    h1 = _auth(client, "h1@example.com")
    h2 = _auth(client, "h2@example.com")
    entry_id = _add(client, h1).json()["id"]
    assert client.get(f"{API}/history", headers=h2).json() == []
    r = client.patch(f"{API}/history/{entry_id}", headers=h2, json={"title": "x"})
    assert r.status_code == 404
