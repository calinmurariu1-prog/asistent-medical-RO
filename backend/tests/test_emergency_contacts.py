from sqlalchemy import select

from app.models.patient import EmergencyContact
from app.models.user import AuditLog
from tests.test_gdpr import API, _auth


def test_contacts_crud_owner_isolation_export_and_erasure(client, db_session):
    h = _auth(client, "contact-owner@example.com")
    other = _auth(client, "contact-other@example.com")
    url = f"{API}/patients/me/emergency-contacts"
    for invalid in ({"name": " "}, {"name": "x" * 201}, {"name": "Test", "phone": "x" * 41}):
        assert client.post(url, headers=h, json=invalid).status_code == 422
    created = client.post(url, headers=h, json={"name": " Fictitious contact ", "phone": "0000"})
    assert created.status_code == 201
    contact = created.json()
    assert contact["name"] == "Fictitious contact"
    item = f"{url}/{contact['id']}"
    assert client.get(url, headers=other).json() == []
    assert client.put(item, headers=other, json={"name": "Foreign edit"}).status_code == 404
    assert client.delete(item, headers=other).status_code == 404
    changed = client.put(item, headers=h, json={"name": "Updated fictitious contact",
                                               "relationship_label": "Friend", "phone": None})
    assert changed.status_code == 200 and changed.json()["phone"] is None
    data = client.get(f"{API}/gdpr/export", headers=h).json()
    assert data["emergency_contacts"][0]["relationship_label"] == "Friend"
    assert client.delete(item, headers=h).status_code == 204
    assert client.get(url, headers=h).json() == []
    entries = list(db_session.scalars(select(AuditLog).where(
        AuditLog.resource_type == "emergency_contact")))
    assert {entry.action for entry in entries} == {
        "emergency_contact.create", "emergency_contact.update", "emergency_contact.delete"}
    assert all(entry.detail is None for entry in entries)
    assert client.post(url, headers=h, json={"name": "Erase me"}).status_code == 201
    assert client.post(f"{API}/gdpr/delete-account", headers=h,
                       json={"password": "Parola1234", "confirm": True}).status_code == 204
    assert list(db_session.scalars(select(EmergencyContact))) == []
