"""Stripe web subscriptions: Checkout, Billing Portal and webhook sync.

Real calls use the `stripe` SDK; without a secret key (and with
`STRIPE_ALLOW_MOCK`) the gateway returns mock URLs so the flow works in
dev/tests. Subscription state is updated from webhook events, same as prod.
"""
from app.services.billing.stripe_pay import gateway, webhooks

__all__ = ["gateway", "webhooks"]
