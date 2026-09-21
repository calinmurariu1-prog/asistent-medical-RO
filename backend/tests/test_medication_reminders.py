"""Explicit medication schedules: ownership, DST, durable advancement and cancellation."""
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.models.medication import Medication
from app.models.medication_reminder import MedicationReminder
from app.models.notification import Notification
from app.services.medication_reminders import advance_due, next_due, obsolete
from tests.test_medications import _auth

API = "/api/v1"


def setup(client):
    headers = _auth(client)
    med = client.post(f"{API}/medications", headers=headers,
                      json={"name": "Tratament fictiv"}).json()
    return headers, med["id"]


def test_schedule_dst_gaps_folds_and_treatment_dates():
    med = Medication(is_active=True)
    reminder = MedicationReminder(local_time="03:30", timezone="Europe/Bucharest", is_enabled=True)
    assert next_due(med, reminder, datetime(2026, 3, 28, 23, tzinfo=UTC)) == datetime(
        2026, 3, 30, 0, 30, tzinfo=UTC)  # Missing spring clock hour is skipped.
    assert next_due(med, reminder, datetime(2026, 10, 24, 23, tzinfo=UTC)) == datetime(
        2026, 10, 25, 0, 30, tzinfo=UTC)
    assert next_due(med, reminder, datetime(2026, 10, 25, 0, 40, tzinfo=UTC)) == datetime(
        2026, 10, 26, 1, 30, tzinfo=UTC)  # No second notification in the repeated hour.
    med.start_date = date(2030, 1, 10)
    med.end_date = date(2030, 1, 10)
    assert next_due(med, reminder, datetime(2026, 1, 1, tzinfo=UTC)) == datetime(
        2030, 1, 10, 1, 30, tzinfo=UTC)
    assert next_due(med, reminder, datetime(2030, 1, 11, tzinfo=UTC)) is None
    med.is_active = False
    assert next_due(med, reminder, datetime(2026, 1, 1, tzinfo=UTC)) is None


def test_schedule_crud_isolation_validation_and_medication_lifecycle(client, db_session):
    h, med_id = setup(client)
    other = _auth(client, "other-reminder@example.com")
    url = f"{API}/medications/{med_id}/reminders"
    payload = {"local_time": "09:00", "timezone": "Europe/Bucharest"}
    for invalid in ({**payload, "local_time": "25:00"}, {**payload, "timezone": "Invalid/Zone"},
                    {"local_time": "09:00"}):
        assert client.post(url, headers=h, json=invalid).status_code == 422
    assert client.post(url, headers=other, json=payload).status_code == 404
    created = client.post(url, headers=h, json=payload)
    assert created.status_code == 201, created.text
    row = created.json()
    assert row["next_occurrence"].endswith("+00:00")
    assert client.post(url, headers=h, json=payload).status_code == 409
    assert client.get(url, headers=other).status_code == 404
    item = url + f"/{row['id']}"
    assert client.put(item, headers=other, json=payload).status_code == 404
    assert client.delete(item, headers=other).status_code == 404
    assert len(client.get(f"{API}/notifications", headers=h).json()) == 1
    assert client.get(f"{API}/gdpr/export", headers=h).json()["medication_reminders"][0][
        "medication_id"] == med_id
    assert client.put(item, headers=h, json={**payload, "is_enabled": False}).status_code == 200
    assert client.get(f"{API}/notifications", headers=h).json() == []
    assert client.put(item, headers=h, json=payload).status_code == 200
    client.patch(f"{API}/medications/{med_id}", headers=h, json={"is_active": False})
    assert client.get(url, headers=h).json()[0]["next_occurrence"] is None
    assert client.get(f"{API}/notifications", headers=h).json() == []
    client.patch(f"{API}/medications/{med_id}", headers=h, json={"is_active": True})
    assert len(client.get(f"{API}/notifications", headers=h).json()) == 1
    assert client.delete(f"{API}/medications/{med_id}", headers=h).status_code == 204
    assert db_session.get(MedicationReminder, row["id"], populate_existing=True) is None
    assert client.get(f"{API}/notifications", headers=h).json() == []


def test_advancement_is_idempotent_and_does_not_backfill_missed_days(client, db_session):
    h, med_id = setup(client)
    row = client.post(f"{API}/medications/{med_id}/reminders", headers=h,
                      json={"local_time": "09:00", "timezone": "UTC"}).json()
    reminder = db_session.get(MedicationReminder, row["id"])
    now = datetime.now(UTC)
    reminder.next_occurrence = now - timedelta(days=7)
    notification = db_session.scalar(select(Notification))
    notification.scheduled_for = reminder.next_occurrence
    db_session.commit()
    assert obsolete(db_session, notification, now)
    assert advance_due(db_session, now) == 1
    assert advance_due(db_session, now) == 0
    assert len(list(db_session.scalars(select(Notification)))) == 2
    db_session.refresh(reminder)
    assert reminder.next_occurrence.replace(tzinfo=UTC) > now


def test_postgres_schedule_advancement_is_serialized(client, db_session):
    from concurrent.futures import ThreadPoolExecutor

    import pytest
    from sqlalchemy.orm import Session

    if db_session.bind.dialect.name != "postgresql":
        pytest.skip("Independent PostgreSQL connections required")
    h, med_id = setup(client)
    created = client.post(f"{API}/medications/{med_id}/reminders", headers=h,
                          json={"local_time": "09:00", "timezone": "UTC"}).json()
    row = db_session.get(MedicationReminder, created["id"])
    now = datetime.now(UTC)
    row.next_occurrence = now - timedelta(minutes=1)
    db_session.commit()
    def run():
        with Session(db_session.bind, expire_on_commit=False) as session:
            return advance_due(session, now)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sum(results) == 1
    assert len(list(db_session.scalars(select(Notification)))) == 2


def test_expired_medication_push_is_not_sent(client, db_session):
    from app.services.notification_delivery import process_due
    from app.services.push.mock import MockPushProvider

    h, med_id = setup(client)
    client.post(f"{API}/notifications/push-token", headers=h,
                json={"token": "fictitious-reminder-device", "platform": "android"})
    client.post(f"{API}/medications/{med_id}/reminders", headers=h,
                json={"local_time": "09:00", "timezone": "UTC"})
    row = db_session.scalar(select(Notification))
    row.scheduled_for = datetime.now(UTC) - timedelta(minutes=16)
    db_session.commit()
    provider = MockPushProvider()
    provider.name = "fcm-test"
    assert process_due(db_session, provider) == 0
    assert not provider.sent
    db_session.refresh(row)
    assert row.status.value == "failed"


def test_schedule_limit_and_account_erasure(client, db_session):
    h, med_id = setup(client)
    for hour in range(12):
        assert client.post(f"{API}/medications/{med_id}/reminders", headers=h,
                           json={"local_time": f"{hour:02}:00", "timezone": "UTC"}
                           ).status_code == 201
    assert client.post(f"{API}/medications/{med_id}/reminders", headers=h,
                       json={"local_time": "23:00", "timezone": "UTC"}).status_code == 422
    assert len(list(db_session.scalars(select(MedicationReminder)))) == 12
    assert len(list(db_session.scalars(select(Notification)))) == 12
    assert client.post(f"{API}/gdpr/delete-account", headers=h,
                       json={"password": "Parola1234", "confirm": True}).status_code == 204
    assert list(db_session.scalars(select(MedicationReminder))) == []
    assert list(db_session.scalars(select(Notification))) == []
