"""Deterministic offline verifier for dev/tests (no store calls).

Treats any token as valid unless it starts with "invalid". Grants the plan that
the product ID maps to, with a one-month expiry, so the full purchase→activate
flow can be exercised without real store credentials.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models.enums import BillingProvider
from app.services.billing.iap.base import PurchaseVerification
from app.services.billing.iap.products import plan_for_product


class MockVerifier:
    def __init__(self, provider: BillingProvider = BillingProvider.MANUAL) -> None:
        self.provider = provider

    def verify(self, *, product_id: str, token: str) -> PurchaseVerification:
        if token.startswith("invalid"):
            return PurchaseVerification(
                valid=False, provider=self.provider, product_id=product_id,
                error="Token invalid (mock).",
            )
        plan = plan_for_product(product_id)
        if plan is None:
            return PurchaseVerification(
                valid=False, provider=self.provider, product_id=product_id,
                error=f"Produs necunoscut: {product_id}",
            )
        return PurchaseVerification(
            valid=True,
            provider=self.provider,
            product_id=product_id,
            plan=plan,
            transaction_id=f"mock-{token}",
            expires_at=datetime.now(UTC) + timedelta(days=30),
            environment="sandbox",
            auto_renewing=True,
            raw={"mock": True, "token": token},
        )
