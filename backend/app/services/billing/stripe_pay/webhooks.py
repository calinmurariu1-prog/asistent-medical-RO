"""Stripe webhook parsing + event handling (keeps Subscription in sync)."""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import (
    BillingProvider,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.models.subscription import Subscription
from app.models.user import User
from app.services.billing.service import ensure_subscription, find_by_customer
from app.services.billing.stripe_pay.prices import plan_for_price

logger = logging.getLogger(__name__)

_STATUS_MAP = {
    "active": SubscriptionStatus.ACTIVE,
    "trialing": SubscriptionStatus.TRIALING,
    "past_due": SubscriptionStatus.PAST_DUE,
    "canceled": SubscriptionStatus.CANCELED,
    "unpaid": SubscriptionStatus.PAST_DUE,
    "incomplete": SubscriptionStatus.PAST_DUE,
    "incomplete_expired": SubscriptionStatus.EXPIRED,
}


def construct_event(payload: bytes, signature: str | None) -> dict:
    """Verify (when a webhook secret is set) and return the event as a dict."""
    if settings.STRIPE_WEBHOOK_SECRET:
        import stripe

        event = stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
        return event if isinstance(event, dict) else event.to_dict()
    # Dev/mock: no secret configured — trust the JSON body.
    return json.loads(payload)


def _ts(value) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value), tz=UTC)
    except (TypeError, ValueError, OSError):
        return None


def handle_event(db: Session, event: dict) -> None:
    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})
    if etype == "checkout.session.completed":
        _on_checkout_completed(db, obj)
    elif etype in ("customer.subscription.updated", "customer.subscription.created"):
        _on_subscription_updated(db, obj)
    elif etype == "customer.subscription.deleted":
        _on_subscription_deleted(db, obj)
    else:
        logger.debug("[stripe] ignoring event %s", etype)


def _on_checkout_completed(db: Session, session: dict) -> None:
    user_id = session.get("client_reference_id") or (
        session.get("metadata", {}) or {}
    ).get("user_id")
    if not user_id:
        logger.info("[stripe] checkout without user reference; skipping")
        return
    user = db.get(User, int(user_id))
    if user is None:
        return
    plan_name = (session.get("metadata", {}) or {}).get("plan")
    plan = SubscriptionPlan(plan_name) if plan_name else SubscriptionPlan.PREMIUM

    sub = ensure_subscription(db, user)
    sub.plan = plan
    sub.status = SubscriptionStatus.ACTIVE
    sub.provider = BillingProvider.STRIPE
    sub.external_customer_id = session.get("customer") or sub.external_customer_id
    sub.external_subscription_id = (
        session.get("subscription") or sub.external_subscription_id
    )
    db.add(sub)
    db.commit()


def _subscription_plan(stripe_sub: dict) -> SubscriptionPlan | None:
    items = (stripe_sub.get("items", {}) or {}).get("data", [])
    if not items:
        return None
    price_id = (items[0].get("price", {}) or {}).get("id")
    return plan_for_price(price_id) if price_id else None


def _on_subscription_updated(db: Session, stripe_sub: dict) -> None:
    sub = _locate(db, stripe_sub)
    if sub is None:
        return
    plan = _subscription_plan(stripe_sub)
    status = _STATUS_MAP.get(stripe_sub.get("status", ""), SubscriptionStatus.ACTIVE)
    active = status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)

    sub.status = status
    sub.provider = BillingProvider.STRIPE
    sub.plan = plan if (plan and active) else SubscriptionPlan.FREE
    sub.current_period_end = _ts(stripe_sub.get("current_period_end"))
    sub.cancel_at_period_end = bool(stripe_sub.get("cancel_at_period_end", False))
    sub.external_subscription_id = stripe_sub.get("id") or sub.external_subscription_id
    db.add(sub)
    db.commit()


def _on_subscription_deleted(db: Session, stripe_sub: dict) -> None:
    sub = _locate(db, stripe_sub)
    if sub is None:
        return
    sub.plan = SubscriptionPlan.FREE
    sub.status = SubscriptionStatus.CANCELED
    sub.cancel_at_period_end = False
    db.add(sub)
    db.commit()


def _locate(db: Session, stripe_sub: dict) -> Subscription | None:
    """Find our subscription from a Stripe subscription object."""
    customer = stripe_sub.get("customer")
    if customer:
        found = find_by_customer(db, customer)
        if found:
            return found
    user_id = (stripe_sub.get("metadata", {}) or {}).get("user_id")
    if user_id:
        user = db.get(User, int(user_id))
        if user:
            return ensure_subscription(db, user)
    return None
