"""Plan <-> Stripe Price ID mapping (from settings)."""
from __future__ import annotations

from app.core.config import settings
from app.models.enums import SubscriptionPlan


def price_map() -> dict[SubscriptionPlan, str]:
    """Parse `STRIPE_PRICES` ("plan:price_id,plan:price_id") into a dict."""
    out: dict[SubscriptionPlan, str] = {}
    for pair in settings.STRIPE_PRICES.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        plan_name, price_id = (p.strip() for p in pair.split(":", 1))
        try:
            out[SubscriptionPlan(plan_name)] = price_id
        except ValueError:
            continue
    return out


def price_for_plan(plan: SubscriptionPlan) -> str | None:
    return price_map().get(plan)


def plan_for_price(price_id: str) -> SubscriptionPlan | None:
    for plan, pid in price_map().items():
        if pid == price_id:
            return plan
    return None
