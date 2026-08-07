"""Shared types and the verifier interface for In-App Purchases.

A verifier takes a store receipt/token, validates it with the store, and returns
a normalized `PurchaseVerification`. Concrete verifiers (Apple / Google / mock)
implement the same interface; the factory selects one per platform and degrades
to the mock when store credentials are absent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from app.models.enums import BillingProvider, SubscriptionPlan


@dataclass
class PurchaseVerification:
    """Normalized result of validating a store purchase."""

    valid: bool
    provider: BillingProvider
    product_id: str = ""
    plan: SubscriptionPlan | None = None
    transaction_id: str | None = None      # original transaction / order id
    expires_at: datetime | None = None
    environment: str = "production"        # "production" | "sandbox"
    auto_renewing: bool = True
    raw: dict = field(default_factory=dict)
    error: str | None = None

    @property
    def is_active(self) -> bool:
        """Valid and not past its expiry (best-effort; None expiry = active)."""
        if not self.valid:
            return False
        if self.expires_at is None:
            return True
        exp = self.expires_at
        from datetime import UTC

        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=UTC)
        return exp >= datetime.now(UTC)


class IAPVerifier(Protocol):
    provider: BillingProvider

    def verify(self, *, product_id: str, token: str) -> PurchaseVerification:
        """Validate a purchase. `token` is the platform receipt/purchase token."""
        ...
