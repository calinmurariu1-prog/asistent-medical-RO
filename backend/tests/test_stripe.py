"""Tests for Stripe web subscriptions (mock gateway + webhook sync)."""
from __future__ import annotations

from sqlalchemy import select

from app.models.user import User

API = "/api/v1"


def _auth(client, email="stripe@example.com"):
    client.post(f"{API}/auth/register", json={"email": email, "password": "Parola1234"})
    tokens = client.post(
        f"{API}/auth/login", json={"email": email, "password": "Parola1234"}
    ).json()
    return {"Authorization": f"Bearer {tokens['access_token']}"}


def _user_id(db_session, email):
    return db_session.scalar(select(User).where(User.email == email)).id


def test_checkout_returns_url(client):
    h = _auth(client)
    r = client.post(f"{API}/billing/stripe/checkout", headers=h, json={"plan": "premium"})
    assert r.status_code == 200, r.text
    assert "mock=1" in r.json()["url"]
    assert "plan=premium" in r.json()["url"]


def test_checkout_free_rejected(client):
    h = _auth(client, email="stripe-free@example.com")
    r = client.post(f"{API}/billing/stripe/checkout", headers=h, json={"plan": "free"})
    assert r.status_code == 400


def test_portal_returns_url(client):
    h = _auth(client, email="stripe-portal@example.com")
    r = client.post(f"{API}/billing/stripe/portal", headers=h)
    assert r.status_code == 200
    assert "mock=portal" in r.json()["url"]


def test_webhook_checkout_completed_activates_premium(client, db_session):
    email = "stripe-wh@example.com"
    h = _auth(client, email=email)
    uid = _user_id(db_session, email)

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": str(uid),
                "customer": "cus_123",
                "subscription": "sub_123",
                "metadata": {"user_id": str(uid), "plan": "premium"},
            }
        },
    }
    r = client.post(f"{API}/billing/stripe/webhook", json=event)
    assert r.status_code == 200

    sub = client.get(f"{API}/billing/subscription", headers=h).json()
    assert sub["plan"] == "premium"
    assert sub["provider"] == "stripe"


def test_webhook_subscription_deleted_downgrades(client, db_session):
    email = "stripe-del@example.com"
    h = _auth(client, email=email)
    uid = _user_id(db_session, email)

    # Activate first (sets external_customer_id = cus_del).
    client.post(
        f"{API}/billing/stripe/webhook",
        json={
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(uid),
                    "customer": "cus_del",
                    "subscription": "sub_del",
                    "metadata": {"plan": "premium"},
                }
            },
        },
    )
    assert client.get(f"{API}/billing/subscription", headers=h).json()["plan"] == "premium"

    # Cancellation event → back to free.
    r = client.post(
        f"{API}/billing/stripe/webhook",
        json={
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_del", "id": "sub_del"}},
        },
    )
    assert r.status_code == 200
    assert client.get(f"{API}/billing/subscription", headers=h).json()["plan"] == "free"


def test_webhook_subscription_updated_maps_price(client, db_session, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "STRIPE_PRICES", "premium:price_prem,family:price_fam")
    email = "stripe-upd@example.com"
    h = _auth(client, email=email)
    uid = _user_id(db_session, email)

    # Seed a customer id via checkout completion.
    client.post(
        f"{API}/billing/stripe/webhook",
        json={
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(uid),
                    "customer": "cus_upd",
                    "subscription": "sub_upd",
                    "metadata": {"plan": "premium"},
                }
            },
        },
    )
    # Update event carrying the family price → plan becomes family.
    r = client.post(
        f"{API}/billing/stripe/webhook",
        json={
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "customer": "cus_upd",
                    "id": "sub_upd",
                    "status": "active",
                    "cancel_at_period_end": False,
                    "current_period_end": 4102444800,
                    "items": {"data": [{"price": {"id": "price_fam"}}]},
                }
            },
        },
    )
    assert r.status_code == 200
    assert client.get(f"{API}/billing/subscription", headers=h).json()["plan"] == "family"
