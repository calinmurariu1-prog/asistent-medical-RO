"""Profile updates validate storage bounds and audit no medical values."""
import json

from sqlalchemy import select

from app.core.security import decrypt_field
from app.models.patient import Patient
from app.models.user import AuditLog, User
from tests.test_gdpr import API, _auth


def test_profile_bounds_and_unknown_doctor_do_not_change_record(client):
    h = _auth(client, "profile-bounds@example.com")
    assert client.put(f"{API}/patients/me", headers=h,
                      json={"first_name": "Fictitious"}).status_code == 200
    for values in ({"first_name": "x" * 121}, {"last_name": "x" * 121},
                   {"phone": "x" * 41}, {"family_doctor_id": 0}):
        assert client.put(f"{API}/patients/me", headers=h, json=values).status_code == 422
    assert client.put(f"{API}/patients/me", headers=h,
                      json={"family_doctor_id": 999999, "first_name": "Must not persist"}
                      ).status_code == 404
    assert client.get(f"{API}/patients/me", headers=h).json()["first_name"] == "Fictitious"


def test_profile_identifier_clear_and_private_audit(client, db_session):
    h = _auth(client, "profile-identifier@example.com")
    other = _auth(client, "profile-other@example.com")
    response = client.put(f"{API}/patients/me", headers=h,
                          json={"cnp": "0000000000000", "first_name": "Synthetic private name"})
    assert response.status_code == 200
    assert "0000000000000" not in response.text
    user = db_session.scalar(select(User).where(User.email == "profile-identifier@example.com"))
    patient = db_session.scalar(select(Patient).where(Patient.user_id == user.id))
    assert decrypt_field(patient.cnp_encrypted) == "0000000000000"
    client.put(f"{API}/patients/me", headers=h, json={"phone": "0000"})
    db_session.refresh(patient)
    assert decrypt_field(patient.cnp_encrypted) == "0000000000000"  # Omission preserves it.
    assert client.put(f"{API}/patients/me", headers=h, json={"cnp": None}).status_code == 200
    db_session.refresh(patient)
    assert patient.cnp_encrypted is None
    assert client.get(f"{API}/patients/me", headers=other).json()["first_name"] is None
    entries = list(db_session.scalars(select(AuditLog).where(
        AuditLog.user_id == user.id, AuditLog.action == "patient_update").order_by(AuditLog.id)))
    assert len(entries) == 3
    assert json.loads(entries[0].detail) == {"fields": ["cnp", "first_name"]}
    assert all("Synthetic private name" not in entry.detail and "0000" not in entry.detail
               for entry in entries)
