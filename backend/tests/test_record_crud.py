"""Medical record edits preserve isolation and reject invalid input."""
import pytest
from sqlalchemy import select

from app.models.user import AuditLog

API = "/api/v1"


def auth(client, email):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    token = client.post(f"{API}/auth/login", json={
        "email": email, "password": "Parola1234"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.parametrize("endpoint,method,payload,key", [
    ("/history", "PATCH", {"title": "Observație fictivă", "event_type": "observation"}, "title"),
    ("/patients/me/allergies", "PUT", {"substance": "Alergen fictiv"}, "substance"),
    ("/history/vaccines", "PUT", {"name": "Vaccin fictiv"}, "name"),
])
def test_record_crud_isolated(client, db_session, endpoint, method, payload, key):
    h = auth(client, "record@example.com")
    other = auth(client, "other-record@example.com")
    created = client.post(API + endpoint, headers=h, json=payload)
    assert created.status_code == 201
    record_id = created.json()["id"]
    url = f"{API}{endpoint}/{record_id}"
    changed = {**payload, key: "Corectat fictiv"}
    assert client.request(method, url, headers=other, json=changed).status_code == 404
    assert client.delete(url, headers=other).status_code == 404
    assert client.get(API + endpoint, headers=other).json() == []
    updated = client.request(method, url, headers=h, json=changed)
    assert updated.status_code == 200
    assert client.get(API + endpoint, headers=h).json()[0][key] == "Corectat fictiv"
    assert client.delete(url, headers=h).status_code == 204
    assert client.get(API + endpoint, headers=h).json() == []
    logs = list(db_session.scalars(select(AuditLog).where(
        AuditLog.resource_type.in_(["medical_history", "allergy", "vaccine"]))))
    assert len(logs) == 3
    assert all(not row.detail for row in logs)  # No medical text in audit details.


def test_invalid_record_inputs_return_validation_errors(client):
    h = auth(client, "validate-record@example.com")
    assert client.post(f"{API}/patients/me/allergies", headers=h,
                       json={"substance": "   "}).status_code == 422
    assert client.post(f"{API}/history/vaccines", headers=h,
                       json={"name": "   "}).status_code == 422
    created = client.post(f"{API}/history", headers=h,
                          json={"title": "Test", "event_type": "observation"}).json()
    for key in ("title", "event_type", "is_chronic"):
        assert client.patch(f"{API}/history/{created['id']}", headers=h,
                            json={key: None}).status_code == 422
    assert client.post(f"{API}/history", headers=h, json={
        "title": "Test", "event_type": "diagnosis", "diagnosis_id": 98765}).status_code == 422
