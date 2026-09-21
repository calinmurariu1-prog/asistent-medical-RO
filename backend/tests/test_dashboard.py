"""Tests for Module 12 - Aggregated dashboard."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="dash@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_empty_dashboard(client):
    h = _auth(client)
    body = client.get(f"{API}/dashboard", headers=h).json()
    assert body["lab_summary"]["total_analytes"] == 0
    assert body["active_medications"] == []
    assert body["upcoming_appointments"] == []
    assert body["unread_notifications"] == 0


def test_dashboard_aggregates_everything(client):
    h = _auth(client)
    client.post(f"{API}/labs", headers=h, json={
        "analyte": "Glicemie", "value": 200, "unit": "mg/dL",
        "ref_low": 70, "ref_high": 99, "measured_on": "2026-01-10"})
    client.post(f"{API}/medications", headers=h,
                json={"name": "Metformin", "active_substance": "metformin"})
    client.post(f"{API}/appointments", headers=h,
                json={"title": "Diabetolog", "starts_at": "2027-05-01T10:00:00Z"})
    client.post(f"{API}/notifications", headers=h,
                json={"title": "Reminder", "scheduled_for": "2030-01-01T09:00:00Z"})

    body = client.get(f"{API}/dashboard", headers=h).json()
    assert body["lab_summary"]["total_analytes"] == 1
    assert body["lab_summary"]["critical_count"] == 0
    assert body["lab_summary"]["abnormal_count"] == 1
    assert len(body["active_medications"]) == 1
    assert len(body["upcoming_appointments"]) == 1
    assert body["unread_notifications"] == 1
    assert body["alerts"] == []  # No unsupported critical threshold inferred.


def test_unevaluable_results_are_counted_separately(client):
    h = _auth(client)
    client.post(f"{API}/labs", headers=h, json={"analyte": "Test", "value": 20})
    result = client.get(f"{API}/dashboard", headers=h).json()["lab_summary"]
    assert result["unknown_count"] == 1
    assert result["abnormal_count"] == 0
    assert result["critical_count"] == 0
    text = client.post(f"{API}/ai/summarize-record", headers=h).json()["result"]
    assert "neevaluabile" in text
