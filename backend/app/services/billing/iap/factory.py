"""Select an IAP verifier per platform, degrading to the mock verifier."""
from __future__ import annotations

import logging

from app.core.config import settings
from app.models.enums import BillingProvider
from app.services.billing.iap.base import IAPVerifier
from app.services.billing.iap.mock import MockVerifier

logger = logging.getLogger(__name__)


def get_verifier(provider: BillingProvider) -> IAPVerifier:
    """Return the real verifier when store credentials are configured, else mock.

    The mock is only used when `IAP_ALLOW_MOCK` is on (default; disable in
    production once real store credentials are in place).
    """
    try:
        if provider == BillingProvider.APPLE:
            from app.services.billing.iap.apple import AppleVerifier

            return AppleVerifier()
        if provider == BillingProvider.GOOGLE:
            from app.services.billing.iap.google import GoogleVerifier

            return GoogleVerifier()
    except Exception as exc:  # noqa: BLE001  (missing creds/SDK)
        if not settings.IAP_ALLOW_MOCK:
            raise
        logger.info("IAP provider %s not configured (%s); using mock.", provider, exc)

    if not settings.IAP_ALLOW_MOCK:
        raise RuntimeError(f"IAP provider {provider} not configured")
    return MockVerifier(provider=provider)
