"""Tests for push-notification token registration + sending (mock sender)."""
from __future__ import annotations

API = "/api/v1"


def _auth(client, email="push@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_register_and_test_push(client):
    h = _auth(client)
    r = client.post(
        f"{API}/notifications/push-token",
        headers=h,
        json={"token": "device-token-123", "platform": "android"},
    )
    assert r.status_code == 204

    sent = client.post(f"{API}/notifications/test-push", headers=h).json()
    assert sent["delivered"] == 0
    assert sent["simulated"] == 1


def test_no_devices_delivers_zero(client):
    h = _auth(client, email="push-none@example.com")
    sent = client.post(f"{API}/notifications/test-push", headers=h).json()
    assert sent["delivered"] == 0


def test_register_is_idempotent(client):
    h = _auth(client, email="push-idem@example.com")
    for _ in range(3):
        client.post(
            f"{API}/notifications/push-token",
            headers=h,
            json={"token": "same-token", "platform": "ios"},
        )
    # Still exactly one device -> one delivery.
    assert client.post(f"{API}/notifications/test-push", headers=h).json()["simulated"] == 1


def test_failed_delivery_preserves_token_for_retry(client):
    h = _auth(client, email="push-bad@example.com")
    client.post(f"{API}/notifications/push-token", headers=h,
                json={"token": "invalid-token", "platform": "android"})
    for _ in range(2):
        result = client.post(f"{API}/notifications/test-push", headers=h).json()
        assert result == {"delivered": 0, "simulated": 0, "failed": 1, "devices": 1}


def test_delete_push_token(client):
    h = _auth(client, email="push-del@example.com")
    client.post(
        f"{API}/notifications/push-token",
        headers=h,
        json={"token": "tok-del", "platform": "web"},
    )
    r = client.request(
        "DELETE",
        f"{API}/notifications/push-token",
        headers=h,
        json={"token": "tok-del"},
    )
    assert r.status_code == 204
    assert client.post(f"{API}/notifications/test-push", headers=h).json()["delivered"] == 0


def test_other_account_cannot_unregister_device(client):
    owner = _auth(client, "push-owner@example.com")
    other = _auth(client, "push-other@example.com")
    payload = {"token": "private-owner-device", "platform": "android"}
    client.post(f"{API}/notifications/push-token", headers=owner, json=payload)
    assert client.request("DELETE", f"{API}/notifications/push-token",
                          headers=other, json=payload).status_code == 204
    assert client.post(f"{API}/notifications/test-push", headers=owner).json()["devices"] == 1
    assert client.post(f"{API}/notifications/test-push", headers=other).json()["devices"] == 0


def test_invalid_device_registration_is_rejected(client):
    headers = _auth(client)
    for payload in ({"token": " "}, {"token": "x" * 401},
                    {"token": "valid", "platform": "unrecognized"}):
        assert client.post(f"{API}/notifications/push-token", headers=headers,
                           json=payload).status_code == 422


def test_notification_push_redacts_content_and_mock_is_not_sent(client, db_session, monkeypatch):
    from app.models.notification import Notification
    from app.services.push import service
    from app.services.push.mock import MockPushProvider

    headers = _auth(client)
    client.post(f"{API}/notifications/push-token", headers=headers,
                json={"token": "private-device", "platform": "android"})
    created = client.post(f"{API}/notifications", headers=headers,
                          json={"title": "Sensitive diagnosis",
                                "body": "Sensitive treatment"}).json()
    notification = db_session.get(Notification, created["id"])
    provider = MockPushProvider()
    monkeypatch.setattr(service, "get_push_provider", lambda: provider)
    assert service.send_notification(db_session, notification) == 0
    assert notification.status.value == "pending"
    assert notification.sent_at is None
    message = provider.sent[0][1]
    assert message.title == "Asistent Medical"
    assert "Sensitive" not in message.body
    assert message.data == {"notification_id": notification.id}
    # Only provider acceptance changes delivery state; read/future items are not sent.
    provider.name = "fcm"
    assert service.send_notification(db_session, notification) == 1
    assert notification.status.value == "sent"
    assert notification.sent_at is not None
    assert service.send_notification(db_session, notification) == 0


def test_future_and_non_push_notifications_are_not_dispatched(client, db_session, monkeypatch):
    from app.models.notification import Notification
    from app.services.push import service

    headers = _auth(client)
    def unexpected(*args, **kwargs):
        raise AssertionError("No push expected")
    monkeypatch.setattr(service, "send_to_user", unexpected)
    for payload in ({"title": "Future", "scheduled_for": "2030-01-01T09:00:00Z"},
                    {"title": "Email", "channel": "email"}):
        created = client.post(f"{API}/notifications", headers=headers, json=payload).json()
        notification = db_session.get(Notification, created["id"])
        assert service.send_notification(db_session, notification) == 0


def test_push_failure_logs_do_not_include_content(monkeypatch, caplog):
    from app.services.push.base import PushMessage
    from app.services.push.fcm import FCMPushProvider

    provider = object.__new__(FCMPushProvider)
    def fail():
        raise RuntimeError("private-token-medical-message")
    monkeypatch.setattr(provider, "_access_token", fail)
    assert provider.send("private-token", PushMessage("private-medical")) is False
    assert "RuntimeError" in caplog.text
    assert "private" not in caplog.text
