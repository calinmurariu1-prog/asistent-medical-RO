"""Tests for Module 6 - Unified timeline."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="tl@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_timeline_merges_and_sorts(client):
    h = _auth(client)
    client.post(
        f"{API}/history",
        headers=h,
        json={"event_type": "diagnosis", "title": "Diagnostic vechi", "event_date": "2022-01-01"},
    )
    client.post(
        f"{API}/appointments",
        headers=h,
        json={"title": "Consult recent", "starts_at": "2026-06-01T10:00:00Z"},
    )

    items = client.get(f"{API}/timeline", headers=h).json()
    assert len(items) == 2
    # Newest first: the 2026 appointment precedes the 2022 diagnosis.
    assert items[0]["kind"] == "appointment"
    assert items[1]["kind"] == "history"


def test_timeline_filters(client):
    h = _auth(client)
    client.post(
        f"{API}/history",
        headers=h,
        json={"event_type": "diagnosis", "title": "D", "event_date": "2022-01-01"},
    )
    client.post(
        f"{API}/appointments",
        headers=h,
        json={"title": "A", "starts_at": "2026-06-01T10:00:00Z"},
    )
    assert len(client.get(f"{API}/timeline?year=2022", headers=h).json()) == 1
    only_appts = client.get(f"{API}/timeline?kinds=appointment", headers=h).json()
    assert len(only_appts) == 1
    assert only_appts[0]["kind"] == "appointment"
