"""Tests for In-App Purchase verification + store webhooks (mock verifier)."""
from __future__ import annotations

import base64
import json

API = "/api/v1"


def _auth(client, email="iap@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def test_verify_apple_purchase_activates_premium(client):
    h = _auth(client)
    r = client.post(
        f"{API}/billing/iap/verify",
        headers=h,
        json={"platform": "apple", "product_id": "premium_monthly", "token": "tx123"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["plan"] == "premium"
    assert body["provider"] == "apple"
    assert body["flags"]["advanced_ai"] is True

    # Reflected on the main subscription endpoint.
    sub = client.get(f"{API}/billing/subscription", headers=h).json()
    assert sub["plan"] == "premium"


def test_verify_google_family_plan(client):
    h = _auth(client, email="iap-g@example.com")
    r = client.post(
        f"{API}/billing/iap/verify",
        headers=h,
        json={"platform": "google", "product_id": "family_monthly", "token": "gtok"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["plan"] == "family"
    assert r.json()["provider"] == "google"


def test_invalid_token_rejected(client):
    h = _auth(client, email="iap-bad@example.com")
    r = client.post(
        f"{API}/billing/iap/verify",
        headers=h,
        json={"platform": "apple", "product_id": "premium_monthly", "token": "invalid-x"},
    )
    assert r.status_code == 402


def test_unknown_product_rejected(client):
    h = _auth(client, email="iap-unk@example.com")
    r = client.post(
        f"{API}/billing/iap/verify",
        headers=h,
        json={"platform": "google", "product_id": "no_such_sku", "token": "t"},
    )
    assert r.status_code == 402


def test_bad_platform_rejected(client):
    h = _auth(client, email="iap-plat@example.com")
    r = client.post(
        f"{API}/billing/iap/verify",
        headers=h,
        json={"platform": "stripe", "product_id": "premium_monthly", "token": "t"},
    )
    assert r.status_code == 400


def test_apple_webhook_refund_downgrades(client):
    h = _auth(client)
    # Purchase first so a subscription with the transaction id exists.
    client.post(
        f"{API}/billing/iap/verify",
        headers=h,
        json={"platform": "apple", "product_id": "premium_monthly", "token": "tx999"},
    )
    # The mock stores transaction_id = "mock-tx999"; craft a REVOKE notification.
    txn = {
        "productId": "premium_monthly",
        "originalTransactionId": "mock-tx999",
        "revocationDate": 1000,
    }
    signed_payload = _fake_jws(
        {"notificationType": "REFUND", "data": {"signedTransactionInfo": _fake_jws(txn)}}
    )
    r = client.post(
        f"{API}/billing/iap/apple/notifications",
        json={"signedPayload": signed_payload},
    )
    assert r.status_code == 200
    sub = client.get(f"{API}/billing/subscription", headers=h).json()
    assert sub["plan"] == "free"


def test_google_webhook_envelope_accepted(client):
    # Malformed/unknown notifications must still return 200 (no retry storm).
    data = base64.b64encode(
        json.dumps({"testNotification": {"version": "1.0"}}).encode()
    ).decode()
    r = client.post(
        f"{API}/billing/iap/google/notifications",
        json={"message": {"data": data}},
    )
    assert r.status_code == 200


def _fake_jws(payload: dict) -> str:
    """Build an unsigned compact JWS whose payload decodes to `payload`."""
    header = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{header}.{body}.sig"
