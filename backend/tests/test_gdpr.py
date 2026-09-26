"""Tests for GDPR endpoints: export, consent, account deletion."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="gdpr@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_export_contains_account_and_records(client):
    h = _auth(client)
    client.post(f"{API}/labs", headers=h, json={
        "analyte": "Glicemie", "value": 90, "unit": "mg/dL", "measured_on": "2026-01-10"})
    client.post(f"{API}/medications", headers=h, json={"name": "Metformin"})

    data = client.get(f"{API}/gdpr/export", headers=h).json()
    assert data["account"]["email"] == "gdpr@example.com"
    assert data["lab_results"][0]["analyte"] == "Glicemie"
    assert data["medications"][0]["name"] == "Metformin"


def test_consent_grant_and_revoke(client):
    h = _auth(client)
    r = client.post(f"{API}/gdpr/consents", headers=h,
                    json={"consent_type": "ai_processing", "granted": True})
    assert r.status_code == 201
    consents = client.get(f"{API}/gdpr/consents", headers=h).json()
    assert consents[0]["granted"] is True

    client.post(f"{API}/gdpr/consents", headers=h,
                json={"consent_type": "ai_processing", "granted": False})
    latest = client.get(f"{API}/gdpr/consents", headers=h).json()
    ai = next(c for c in latest if c["consent_type"] == "ai_processing")
    assert ai["granted"] is False  # latest state wins


def test_delete_account_requires_password_and_confirm(client):
    h = _auth(client)
    assert client.request(
        "POST", f"{API}/gdpr/delete-account", headers=h,
        json={"password": "Parola1234", "confirm": False}).status_code == 400
    assert client.request(
        "POST", f"{API}/gdpr/delete-account", headers=h,
        json={"password": "gresit", "confirm": True}).status_code == 401


def test_delete_account_erases_user(client):
    h = _auth(client)
    r = client.request(
        "POST", f"{API}/gdpr/delete-account", headers=h,
        json={"password": "Parola1234", "confirm": True})
    assert r.status_code == 204
    # Token no longer resolves to a user.
    assert client.get(f"{API}/auth/me", headers=h).status_code == 401


def test_export_preserves_clinical_details_and_isolates_accounts(client, db_session):
    from datetime import UTC, date, datetime

    from sqlalchemy import select

    from app.models.appointment import Appointment
    from app.models.chat import AIChat, AIChatMessage
    from app.models.document import Document, LabResult
    from app.models.enums import ChatRole
    from app.models.medication import Medication
    from app.models.patient import EmergencyContact, Patient, Vaccine

    owner = _auth(client, "export-owner@example.com")
    other = _auth(client, "export-other@example.com")
    client.get(f"{API}/documents", headers=owner)
    patient = db_session.scalar(select(Patient))
    document = Document(patient_id=patient.id, original_filename="fictitious.pdf",
                        storage_key="internal-secret-storage-key", extracted_text="Fictitious text",
                        ai_metadata="legacy malformed metadata", document_date=date(2026, 1, 2))
    db_session.add(document)
    db_session.flush()
    db_session.add_all([
        Medication(patient_id=patient.id, name="Synthetic treatment", interval="after meals",
                   start_date=date(2026, 1, 1), end_date=date(2026, 2, 1), notes="Synthetic note"),
        Appointment(patient_id=patient.id, title="Synthetic appointment", location="Test location",
                    starts_at=datetime(2026, 1, 2, 9, tzinfo=UTC),
                    ends_at=datetime(2026, 1, 2, 10, tzinfo=UTC), notes="Bring fictitious record"),
        EmergencyContact(patient_id=patient.id, name="Synthetic contact", phone="0000000000"),
        Vaccine(patient_id=patient.id, name="Synthetic vaccine", provider="Test provider"),
        LabResult(patient_id=patient.id, document_id=document.id, analyte="Synthetic analyte",
                  value_text="negative", confidence="unverified", loinc_code="test-code"),
    ])
    chat = AIChat(patient_id=patient.id, title="Synthetic chat")
    db_session.add(chat)
    db_session.flush()
    db_session.add(AIChatMessage(chat_id=chat.id, role=ChatRole.USER,
                               content="Synthetic message", sources="legacy malformed sources"))
    db_session.commit()
    response = client.get(f"{API}/gdpr/export", headers=owner)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    data = response.json()
    assert data["medications"][0]["notes"] == "Synthetic note"
    assert data["medications"][0]["interval"] == "after meals"
    assert data["medications"][0]["start_date"] == "2026-01-01"
    assert data["medications"][0]["end_date"] == "2026-02-01"
    assert data["appointments"][0]["location"] == "Test location"
    assert data["appointments"][0]["ends_at"] == "2026-01-02T10:00:00+00:00"
    assert data["emergency_contacts"][0]["phone"] == "0000000000"
    assert data["vaccines"][0]["provider"] == "Test provider"
    assert data["lab_results"][0]["confidence"] == "unverified"
    assert data["lab_results"][0]["value_text"] == "negative"
    assert data["lab_results"][0]["document_id"] == document.id
    assert data["documents"][0]["extracted_text"] == "Fictitious text"
    assert data["documents"][0]["ai_metadata"] == {"unparsed_text": "legacy malformed metadata"}
    assert data["documents"][0]["original_download_path"] == (
        f"/api/v1/documents/{document.id}/original")
    assert data["chats"][0]["messages"][0]["sources"] == {
        "unparsed_text": "legacy malformed sources"}
    assert "internal-secret-storage-key" not in response.text
    assert "hashed_password" not in response.text
    assert data["export_metadata"]["original_files_included"] is False
    assert "cnp" in data["export_metadata"]["not_included"]
    assert data["export_metadata"]["schema_version"] == 2
    foreign = client.get(f"{API}/gdpr/export", headers=other)
    assert "Synthetic" not in foreign.text
    path = data["documents"][0]["original_download_path"]
    assert client.get(path, headers=other).status_code == 404
    assert client.get(f"{API}/gdpr/export").status_code == 401


def test_health_notifications_feedback_export_owner_scope(client, db_session):
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.models.enums import HealthMetricType, HealthSource, NotificationChannel
    from app.models.feedback import Feedback
    from app.models.health import HealthSample
    from app.models.health_device import HealthDevice
    from app.models.notification import Notification
    from app.models.patient import Patient
    from app.models.user import User

    headers = []
    for index in range(2):
        email = f"portable-{index}@example.com"
        h = _auth(client, email)
        headers.append(h)
        client.get(f"{API}/documents", headers=h)
        user = db_session.scalar(select(User).where(User.email == email))
        patient = db_session.scalar(select(Patient).where(Patient.user_id == user.id))
        when = datetime(2026, 1, 1, 12, tzinfo=UTC)
        db_session.add_all([
            HealthSample(patient_id=patient.id, source=HealthSource.MANUAL,
                         metric_type=HealthMetricType.STEPS, value=100 + index,
                         unit="count", recorded_at=when),
            HealthDevice(patient_id=patient.id, source=HealthSource.MANUAL,
                         name=f"synthetic-device-{index}", metrics='["steps"]',
                         sample_count=1, last_seen_at=when),
            Notification(user_id=user.id, channel=NotificationChannel.PUSH,
                         title=f"synthetic-notification-{index}", body="Fictitious body",
                         scheduled_for=when, delivery_token="internal-delivery-claim"),
            Feedback(user_id=user.id, message=f"synthetic-feedback-{index}", rating=4),
        ])
        db_session.commit()
    for index, h in enumerate(headers):
        response = client.get(f"{API}/gdpr/export", headers=h)
        assert response.status_code == 200
        data = response.json()
        assert len(data["health_samples"]) == 1
        assert data["health_samples"][0]["value"] == 100 + index
        assert data["health_samples"][0]["recorded_at"] == "2026-01-01T12:00:00+00:00"
        assert data["health_devices"][0]["name"] == f"synthetic-device-{index}"
        assert data["health_devices"][0]["metrics"] == ["steps"]
        assert len(data["notifications"]) == 1
        assert data["notifications"][0]["title"] == f"synthetic-notification-{index}"
        assert data["feedback"][0]["message"] == f"synthetic-feedback-{index}"
        assert "internal-delivery-claim" not in response.text
        assert "delivery_token" not in response.text
        for section in ("health_device_data", "notifications", "feedback"):
            assert section not in data["export_metadata"]["not_included"]


def test_account_export_without_patient_keeps_feedback(client, db_session):
    from sqlalchemy import select

    from app.models.feedback import Feedback
    from app.models.user import User

    h = _auth(client, "no-patient-export@example.com")
    user = db_session.scalar(select(User).where(User.email == "no-patient-export@example.com"))
    db_session.add(Feedback(user_id=user.id, message="Before profile creation"))
    db_session.commit()
    data = client.get(f"{API}/gdpr/export", headers=h).json()
    assert data["patient"] is None
    assert data["feedback"][0]["message"] == "Before profile creation"


def test_export_audit_events_are_owner_scoped_without_internal_detail(client, db_session):
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.models.user import AuditLog, User

    owner = _auth(client, "audit-export-owner@example.com")
    other = _auth(client, "audit-export-other@example.com")
    for email, action in (("audit-export-owner@example.com", "owner_action"),
                          ("audit-export-other@example.com", "other_action")):
        user = db_session.scalar(select(User).where(User.email == email))
        db_session.add(AuditLog(user_id=user.id, action=action, resource_type="patient",
                               ip_address="192.0.2.1", user_agent="Synthetic browser",
                               detail="internal-detail-must-stay-private",
                               created_at=datetime.now(UTC)))
    db_session.add(AuditLog(user_id=None, action="unattributed_action",
                           created_at=datetime.now(UTC)))
    db_session.commit()
    for headers, present, absent in ((owner, "owner_action", "other_action"),
                                     (other, "other_action", "owner_action")):
        response = client.get(f"{API}/gdpr/export", headers=headers)
        assert response.status_code == 200
        events = response.json()["audit_events"]
        assert present in [event["action"] for event in events]
        assert absent not in [event["action"] for event in events]
        assert "unattributed_action" not in response.text
        assert "internal-detail-must-stay-private" not in response.text
        assert all("detail" not in event for event in events)
        assert any(event["action"] == "gdpr_export" for event in events)
        own = next(event for event in events if event["action"] == present)
        assert own["ip_address"] == "192.0.2.1"
        assert own["user_agent"] == "Synthetic browser"
        assert own["created_at"].endswith("+00:00")


def test_export_subscription_without_patient_excludes_provider_secrets(client, db_session):
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.models.subscription import Subscription
    from app.models.user import User

    owner = _auth(client, "subscription-owner@example.com")
    other = _auth(client, "subscription-other@example.com")
    user = db_session.scalar(select(User).where(User.email == "subscription-owner@example.com"))
    row = Subscription(user_id=user.id, cancel_at_period_end=True,
                       current_period_end=datetime(2027, 1, 1, tzinfo=UTC),
                       external_customer_id="private-customer-marker",
                       external_subscription_id="private-purchase-token-marker")
    db_session.add(row)
    db_session.commit()
    response = client.get(f"{API}/gdpr/export", headers=owner)
    assert response.status_code == 200
    data = response.json()
    assert data["patient"] is None
    assert data["subscription"]["id"] == row.id
    assert data["subscription"]["cancel_at_period_end"] is True
    assert data["subscription"]["current_period_end"] == "2027-01-01T00:00:00+00:00"
    assert data["subscription"]["plan"] == row.plan.value
    assert data["subscription"]["status"] == row.status.value
    assert data["subscription"]["provider"] == row.provider.value
    assert data["subscription"]["trial_end"] is None
    assert "private-customer-marker" not in response.text
    assert "private-purchase-token-marker" not in response.text
    assert "billing_provider_identifiers" in data["export_metadata"]["not_included"]
    assert client.get(f"{API}/gdpr/export", headers=other).json()["subscription"] is None
