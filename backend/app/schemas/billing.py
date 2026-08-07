"""Schemas for the SaaS billing / subscription module."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.models.enums import (
    BillingProvider,
    SubscriptionPlan,
    SubscriptionStatus,
)


class PlanOut(BaseModel):
    plan: SubscriptionPlan
    name: str
    price_eur_month: float
    tagline: str
    features: list[str]
    limits: dict[str, int]
    flags: dict[str, bool]


class SubscriptionOut(BaseModel):
    plan: SubscriptionPlan
    plan_name: str
    status: SubscriptionStatus
    provider: BillingProvider
    current_period_end: datetime | None = None
    trial_end: datetime | None = None
    cancel_at_period_end: bool = False
    limits: dict[str, int]
    flags: dict[str, bool]


class ChangePlanRequest(BaseModel):
    plan: SubscriptionPlan
