"""Durable delivery, fencing and appointment reminder lifecycle."""
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.notification import Notification
from app.services.notification_delivery import process_due
from app.services.push.mock import MockPushProvider
from tests.test_notifications import API, _auth


def setup_notification(client, db_session, **payload):
    headers = _auth(client)
    client.post(f"{API}/notifications/push-token", headers=headers,
                json={"token": "fictitious-device", "platform": "android"})
    created = client.post(f"{API}/notifications", headers=headers,
                          json={"title": "Private medical reminder", **payload}).json()
    return headers, db_session.get(Notification, created["id"])


def real_fake():
    provider = MockPushProvider()
    provider.name = "fcm-test"
    return provider


def test_delivery_retries_persistently_and_only_due_rows(client, db_session):
    _, row = setup_notification(client, db_session)
    provider = real_fake()
    provider.send = lambda *args: False
    assert process_due(db_session, provider) == 0
    db_session.refresh(row)
    assert row.delivery_attempts == 1 and row.next_delivery_at is not None
    assert row.sent_at is None and row.delivery_token is None
    assert process_due(db_session, real_fake()) == 0  # Retry not yet due.
    row.next_delivery_at = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()
    accepted = real_fake()
    assert process_due(db_session, accepted) == 1
    db_session.refresh(row)
    assert row.status.value == "sent" and row.sent_at is not None
    assert row.delivery_attempts == 2 and row.next_delivery_at is None
    assert "Private" not in accepted.sent[0][1].body
    assert process_due(db_session, accepted) == 0


def test_expired_delivery_claim_is_recovered_but_live_claim_is_not(client, db_session):
    _, row = setup_notification(client, db_session)
    row.delivery_token = "abandoned"
    row.delivery_until = datetime.now(UTC) + timedelta(minutes=5)
    db_session.commit()
    assert process_due(db_session, real_fake()) == 0
    row.delivery_until = datetime.now(UTC) - timedelta(seconds=1)
    db_session.commit()
    assert process_due(db_session, real_fake()) == 1
    db_session.refresh(row)
    assert row.delivery_token is None


def test_mock_future_and_read_notifications_never_claimed(client, db_session):
    headers, row = setup_notification(client, db_session)
    assert process_due(db_session, MockPushProvider()) == 0
    db_session.refresh(row)
    assert row.delivery_attempts == 0 and row.sent_at is None
    row.scheduled_for = datetime.now(UTC) + timedelta(days=1)
    db_session.commit()
    assert process_due(db_session, real_fake()) == 0
    assert client.post(f"{API}/notifications/read-all", headers=headers).json()["marked_read"] == 0
    client.post(f"{API}/notifications/{row.id}/read", headers=headers)
    row.scheduled_for = datetime.now(UTC) - timedelta(days=1)
    db_session.commit()
    assert process_due(db_session, real_fake()) == 0


def test_stale_delivery_cannot_overwrite_new_claim(client, db_session):
    _, row = setup_notification(client, db_session)
    old = real_fake()
    replacement = real_fake()
    def superseded(*args):
        row.delivery_until = datetime.now(UTC) - timedelta(seconds=1)
        db_session.commit()
        assert process_due(db_session, replacement) == 1
        return False
    old.send = superseded
    assert process_due(db_session, old) == 0
    db_session.refresh(row)
    assert row.status.value == "sent"
    assert row.next_delivery_at is None


def test_appointment_reminder_updates_cancels_and_normalizes_timezone(client, db_session):
    headers = _auth(client)
    created = client.post(f"{API}/appointments", headers=headers, json={
        "title": "Fictitious appointment", "starts_at": "2030-05-01T13:00:00+03:00",
    }).json()
    appointment_id = created["id"]
    assert created["starts_at"] == "2030-05-01T10:00:00+00:00"
    def reminders():
        return list(db_session.scalars(select(Notification).where(
            Notification.resource_type == "appointment",
            Notification.resource_id == str(appointment_id))))
    rows = reminders()
    assert len(rows) == 1
    assert rows[0].scheduled_for.replace(tzinfo=UTC) == datetime(2030, 4, 30, 10, tzinfo=UTC)
    response = client.patch(f"{API}/appointments/{appointment_id}", headers=headers,
                            json={"starts_at": "2030-05-02T10:00:00Z"})
    assert response.status_code == 200
    assert len(reminders()) == 1
    assert reminders()[0].scheduled_for.replace(tzinfo=UTC) == datetime(2030, 5, 1, 10, tzinfo=UTC)
    client.patch(f"{API}/appointments/{appointment_id}", headers=headers,
                 json={"status": "cancelled"})
    assert reminders() == []
    client.patch(f"{API}/appointments/{appointment_id}", headers=headers,
                 json={"status": "scheduled"})
    assert len(reminders()) == 1
    client.delete(f"{API}/appointments/{appointment_id}", headers=headers)
    assert reminders() == []


def test_invalid_appointment_time_does_not_create_reminder(client):
    headers = _auth(client)
    for payload in ({"starts_at": "2030-05-01T10:00:00"},
                    {"starts_at": "2030-05-01T10:00:00Z", "ends_at": "2030-05-01T09:00:00Z"}):
        response = client.post(f"{API}/appointments", headers=headers,
                               json={"title": "Fictitious", **payload})
        assert response.status_code == 422
    assert client.get(f"{API}/notifications", headers=headers).json() == []


def test_postgres_workers_claim_notification_once(client, db_session):
    from concurrent.futures import ThreadPoolExecutor

    import pytest
    from sqlalchemy.orm import Session

    if db_session.bind.dialect.name != "postgresql":
        pytest.skip("Independent PostgreSQL connections required")
    setup_notification(client, db_session)
    provider = real_fake()
    def run():
        with Session(db_session.bind, expire_on_commit=False) as session:
            return process_due(session, provider)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sum(results) == 1
    assert len(provider.sent) == 1
