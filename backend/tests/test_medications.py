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


def test_medication_validation_on_create_and_partial_update(client):
    headers = _auth(client)
    for payload in ({"name": " "}, {"name": "Test", "dose": "x" * 101},
                    {"name": "Test", "start_date": "2030-02-01", "end_date": "2030-01-01"}):
        assert client.post(f"{API}/medications", headers=headers, json=payload).status_code == 422
    created = client.post(f"{API}/medications", headers=headers, json={
        "name": "Fictitious", "start_date": "2030-02-01", "end_date": "2030-02-10",
    }).json()
    for payload in ({"end_date": "2030-01-01"}, {"start_date": "2030-03-01"},
                    {"name": None}, {"is_active": None}):
        assert client.patch(f"{API}/medications/{created['id']}", headers=headers,
                            json=payload).status_code == 422
    row = client.get(f"{API}/medications", headers=headers).json()[0]
    assert row["end_date"] == "2030-02-10" and row["name"] == "Fictitious"


def test_medication_changes_are_owned_and_audited_without_content(client, db_session):
    from sqlalchemy import select

    from app.models.user import AuditLog

    owner = _auth(client, "med-owner@example.com")
    other = _auth(client, "med-other@example.com")
    created = client.post(f"{API}/medications", headers=owner,
                          json={"name": "private-medical-name", "dose": "private-dose"}).json()
    path = f"{API}/medications/{created['id']}"
    assert client.patch(path, headers=other, json={"dose": "different"}).status_code == 404
    assert client.delete(path, headers=other).status_code == 404
    changed = client.patch(path, headers=owner, json={"frequency": "recorded", "is_active": False})
    assert changed.status_code == 200
    assert changed.json()["dose"] == "private-dose"
    assert client.get(f"{API}/medications?active_only=true", headers=owner).json() == []
    assert len(client.get(f"{API}/medications", headers=owner).json()) == 1
    assert client.delete(path, headers=owner).status_code == 204
    logs = list(db_session.scalars(select(AuditLog).where(
        AuditLog.resource_type == "medication", AuditLog.resource_id == str(created["id"])
    ).order_by(AuditLog.id)))
    assert [entry.action for entry in logs] == [
        "medication.create", "medication.update", "medication.delete"]
    assert all(entry.detail is None for entry in logs)


def test_legacy_long_notes_remain_readable(client, db_session):
    from app.models.medication import Medication

    headers = _auth(client)
    result = _add(client, headers, "Fictitious").json()
    row = db_session.get(Medication, result["id"])
    row.notes = "x" * 5000
    db_session.commit()
    response = client.get(f"{API}/medications", headers=headers)
    assert response.status_code == 200
    assert len(response.json()[0]["notes"]) == 5000
