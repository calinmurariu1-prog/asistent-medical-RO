"""In-App Purchase verification (Apple App Store / Google Play).

A verifier validates a store receipt/token and returns a normalized
`PurchaseVerification`; `service.apply_verification` maps it onto the user's
`Subscription`. Store credentials are optional in dev/test — the factory falls
back to a deterministic mock verifier.
"""
from app.services.billing.iap import service
from app.services.billing.iap.base import IAPVerifier, PurchaseVerification
from app.services.billing.iap.factory import get_verifier

__all__ = ["IAPVerifier", "PurchaseVerification", "get_verifier", "service"]
