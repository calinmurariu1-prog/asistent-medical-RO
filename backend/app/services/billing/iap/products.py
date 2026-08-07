"""Store product IDs -> subscription plan mapping (from settings)."""
from __future__ import annotations

from app.core.config import settings
from app.models.enums import SubscriptionPlan


def product_map() -> dict[str, SubscriptionPlan]:
    """Parse `IAP_PRODUCTS` ("prod_id:plan,prod_id:plan") into a dict."""
    out: dict[str, SubscriptionPlan] = {}
    for pair in settings.IAP_PRODUCTS.split(","):
        pair = pair.strip()
        if not pair or ":" not in pair:
            continue
        product_id, plan_name = (p.strip() for p in pair.split(":", 1))
        try:
            out[product_id] = SubscriptionPlan(plan_name)
        except ValueError:
            continue
    return out


def plan_for_product(product_id: str) -> SubscriptionPlan | None:
    return product_map().get(product_id)
