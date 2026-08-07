"""Subscription read/write helpers.

Real billing (Stripe / App Store / Play) is added later; for now a plan change
is recorded directly (provider = manual) so the product, gating and UI can be
built and tested end-to-end.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.enums import (
    BillingProvider,
    SubscriptionPlan,
    SubscriptionStatus,
)
from app.models.subscription import Subscription
from app.models.user import User


def ensure_subscription(db: Session, user: User) -> Subscription:
    """Return the user's subscription row, creating a FREE one if absent."""
    if user.subscription is not None:
        return user.subscription
    sub = Subscription(
        user_id=user.id,
        plan=SubscriptionPlan.FREE,
        status=SubscriptionStatus.ACTIVE,
        provider=BillingProvider.NONE,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def set_plan(
    db: Session,
    user: User,
    plan: SubscriptionPlan,
    *,
    provider: BillingProvider = BillingProvider.MANUAL,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
) -> Subscription:
    """Set (or downgrade to) a plan. Downgrading to FREE resets billing linkage."""
    sub = ensure_subscription(db, user)
    sub.plan = plan
    if plan == SubscriptionPlan.FREE:
        sub.status = SubscriptionStatus.ACTIVE
        sub.provider = BillingProvider.NONE
        sub.current_period_end = None
        sub.external_customer_id = None
        sub.external_subscription_id = None
        sub.cancel_at_period_end = False
    else:
        sub.status = status
        sub.provider = provider
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub
