"""SaaS billing: plan catalog, entitlements and subscription state.

Full payment integration (Stripe on web, In-App Purchase on Apple/Google) is
layered on later; the models and entitlements here are the foundation that
gating and the mobile apps build on.
"""
from app.services.billing import entitlements, iap, service

__all__ = ["entitlements", "iap", "service"]
