"""Stripe gateway: Checkout + Billing Portal sessions.

Real calls use the `stripe` SDK (lazy import). When no secret key is set and
`STRIPE_ALLOW_MOCK` is on, checkout/portal return deterministic mock URLs so the
flow can be built and tested without Stripe credentials — the subscription then
activates via a (mock) webhook event, exactly like production.
"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import SubscriptionPlan
from app.models.user import User
from app.services.billing.service import ensure_subscription
from app.services.billing.stripe_pay.prices import price_for_plan

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def _success_url() -> str:
    return settings.STRIPE_SUCCESS_URL or (
        f"{settings.FRONTEND_URL}/subscription?status=success"
    )


def _cancel_url() -> str:
    return settings.STRIPE_CANCEL_URL or (
        f"{settings.FRONTEND_URL}/subscription?status=cancel"
    )


def _portal_return_url() -> str:
    return settings.STRIPE_PORTAL_RETURN_URL or f"{settings.FRONTEND_URL}/subscription"


def _client():
    import stripe

    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def create_checkout_session(db: Session, user: User, plan: SubscriptionPlan) -> str:
    """Return a Checkout URL for subscribing `user` to `plan`."""
    price = price_for_plan(plan)
    if price is None and is_configured():
        raise ValueError(f"Niciun preț Stripe configurat pentru planul {plan.value}.")

    if not is_configured():
        if not settings.STRIPE_ALLOW_MOCK:
            raise RuntimeError("Stripe nu este configurat.")
        # Mock URL — the client returns to /subscription; activation is simulated
        # via the webhook endpoint in dev/test.
        return f"{_success_url()}&mock=1&plan={plan.value}"

    stripe = _client()
    sub = ensure_subscription(db, user)
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price, "quantity": 1}],
        success_url=_success_url(),
        cancel_url=_cancel_url(),
        client_reference_id=str(user.id),
        customer=sub.external_customer_id or None,
        customer_email=None if sub.external_customer_id else user.email,
        subscription_data={"metadata": {"user_id": str(user.id), "plan": plan.value}},
        metadata={"user_id": str(user.id), "plan": plan.value},
    )
    return session.url


def create_portal_session(db: Session, user: User) -> str:
    """Return a Billing Portal URL for the user to manage their subscription."""
    sub = ensure_subscription(db, user)
    if not is_configured():
        if not settings.STRIPE_ALLOW_MOCK:
            raise RuntimeError("Stripe nu este configurat.")
        return f"{_portal_return_url()}?mock=portal"
    if not sub.external_customer_id:
        raise ValueError("Nu există un client Stripe pentru acest utilizator.")
    stripe = _client()
    session = stripe.billing_portal.Session.create(
        customer=sub.external_customer_id,
        return_url=_portal_return_url(),
    )
    return session.url
