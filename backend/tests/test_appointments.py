"""Tests for Module 10 - Appointments."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="appt@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _create(client, h, title, starts_at, **kw):
    return client.post(
        f"{API}/appointments",
        headers=h,
        json={"title": title, "starts_at": starts_at, **kw},
    )


def test_crud_and_status_update(client):
    h = _auth(client)
    r = _create(client, h, "Cardiolog", "2027-05-01T10:00:00Z", type="consultation")
    assert r.status_code == 201, r.text
    appt_id = r.json()["id"]
    assert r.json()["status"] == "scheduled"

    r = client.patch(
        f"{API}/appointments/{appt_id}", headers=h, json={"status": "completed"}
    )
    assert r.json()["status"] == "completed"

    assert client.get(f"{API}/appointments/{appt_id}", headers=h).json()["id"] == appt_id
    assert client.delete(f"{API}/appointments/{appt_id}", headers=h).status_code == 204


def test_upcoming_filter(client):
    h = _auth(client)
    _create(client, h, "Viitoare", "2027-05-01T10:00:00Z")
    _create(client, h, "Trecuta", "2020-05-01T10:00:00Z")

    all_appts = client.get(f"{API}/appointments", headers=h).json()
    assert len(all_appts) == 2

    upcoming = client.get(f"{API}/appointments?upcoming=true", headers=h).json()
    assert [a["title"] for a in upcoming] == ["Viitoare"]


def test_isolated_per_patient(client):
    h1 = _auth(client, "a1@example.com")
    h2 = _auth(client, "a2@example.com")
    appt_id = _create(client, h1, "X", "2027-05-01T10:00:00Z").json()["id"]
    assert client.get(f"{API}/appointments/{appt_id}", headers=h2).status_code == 404
