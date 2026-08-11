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
    assert sent["delivered"] == 1


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
    assert client.post(f"{API}/notifications/test-push", headers=h).json()["delivered"] == 1


def test_failed_token_is_pruned(client):
    h = _auth(client, email="push-bad@example.com")
    client.post(
        f"{API}/notifications/push-token",
        headers=h,
        json={"token": "invalid-token", "platform": "android"},
    )
    # Mock sender fails "invalid*" tokens; the token is pruned after the attempt.
    assert client.post(f"{API}/notifications/test-push", headers=h).json()["delivered"] == 0
    # Second send finds no devices left.
    assert client.post(f"{API}/notifications/test-push", headers=h).json()["delivered"] == 0


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
