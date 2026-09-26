"""SaaS subscription state for a user (plan, status, billing linkage).

One row per user. A user with no row is treated as the FREE plan. Full billing
(Stripe / App Store / Play) is layered on later; the external_* fields already
model the linkage so provider webhooks can update status in place.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import (
    BillingProvider,
    SubscriptionPlan,
    SubscriptionStatus,
)

if TYPE_CHECKING:
    from app.models.user import User


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscriptions"
    __table_args__ = (UniqueConstraint("user_id", name="uq_subscriptions_user_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    plan: Mapped[SubscriptionPlan] = mapped_column(
        Enum(SubscriptionPlan, native_enum=False, length=20),
        default=SubscriptionPlan.FREE,
        nullable=False,
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, length=20),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
    )
    provider: Mapped[BillingProvider] = mapped_column(
        Enum(BillingProvider, native_enum=False, length=20),
        default=BillingProvider.NONE,
        nullable=False,
    )
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    trial_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    # Provider-side identifiers (Stripe customer/subscription, IAP token, etc.).
    external_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_subscription_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )

    user: Mapped[User] = relationship(back_populates="subscription")
