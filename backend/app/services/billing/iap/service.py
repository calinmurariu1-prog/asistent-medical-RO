"""Apply a verified purchase to a user's subscription."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import SubscriptionPlan, SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.services.billing.iap.base import PurchaseVerification
from app.services.billing.service import ensure_subscription


def apply_verification(
    db: Session, user: User, v: PurchaseVerification
) -> Subscription:
    """Update the user's subscription from a verified purchase.

    An active purchase sets the plan + period end; an inactive/expired one
    reverts the user to FREE (so a lapsed subscription loses entitlements).
    """
    sub = ensure_subscription(db, user)
    sub.provider = v.provider
    sub.external_subscription_id = v.transaction_id

    if v.is_active and v.plan is not None:
        sub.plan = v.plan
        sub.status = SubscriptionStatus.ACTIVE
        sub.current_period_end = v.expires_at
        sub.cancel_at_period_end = not v.auto_renewing
    else:
        sub.plan = SubscriptionPlan.FREE
        sub.status = (
            SubscriptionStatus.EXPIRED if v.valid else SubscriptionStatus.CANCELED
        )
        sub.current_period_end = v.expires_at

    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def find_by_transaction(db: Session, transaction_id: str) -> Subscription | None:
    """Locate a subscription by its store transaction id (for webhooks)."""
    return db.scalar(
        select(Subscription).where(
            Subscription.external_subscription_id == transaction_id
        )
    )
