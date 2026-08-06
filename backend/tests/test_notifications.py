"""Tests for Module 14 - Notifications."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="notif@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_immediate_notification_is_sent(client):
    h = _auth(client)
    r = client.post(
        f"{API}/notifications", headers=h, json={"title": "Ia-ți medicamentul"}
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "sent"
    assert body["sent_at"] is not None


def test_scheduled_notification_is_pending(client):
    h = _auth(client)
    r = client.post(
        f"{API}/notifications",
        headers=h,
        json={"title": "Programare mâine", "scheduled_for": "2030-01-01T09:00:00Z"},
    )
    assert r.json()["status"] == "pending"
    assert r.json()["sent_at"] is None


def test_list_unread_mark_read_and_read_all(client):
    h = _auth(client)
    n1 = client.post(f"{API}/notifications", headers=h, json={"title": "A"}).json()["id"]
    client.post(f"{API}/notifications", headers=h, json={"title": "B"})

    assert len(client.get(f"{API}/notifications", headers=h).json()) == 2
    assert len(client.get(f"{API}/notifications?unread_only=true", headers=h).json()) == 2

    client.post(f"{API}/notifications/{n1}/read", headers=h)
    assert len(client.get(f"{API}/notifications?unread_only=true", headers=h).json()) == 1

    assert client.post(f"{API}/notifications/read-all", headers=h).json()["marked_read"] == 1
    assert client.get(f"{API}/notifications?unread_only=true", headers=h).json() == []


def test_appointment_reminders_are_idempotent(client):
    h = _auth(client)
    client.post(
        f"{API}/appointments",
        headers=h,
        json={"title": "Analize", "starts_at": "2027-05-01T10:00:00Z"},
    )
    first = client.post(f"{API}/notifications/reminders/appointments", headers=h).json()
    assert len(first) == 1
    assert first[0]["resource_type"] == "appointment"

    # Running again does not create a duplicate reminder.
    second = client.post(f"{API}/notifications/reminders/appointments", headers=h).json()
    assert second == []


def test_isolated_per_user(client):
    h1 = _auth(client, "n1@example.com")
    h2 = _auth(client, "n2@example.com")
    nid = client.post(f"{API}/notifications", headers=h1, json={"title": "X"}).json()["id"]
    assert client.post(f"{API}/notifications/{nid}/read", headers=h2).status_code == 404
    assert client.get(f"{API}/notifications", headers=h2).json() == []
