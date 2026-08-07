"""Apple App Store verifier (App Store Server API).

Flow (StoreKit 2): the app sends the `transactionId`. We authenticate to the
App Store Server API with a JWT signed by an App Store Connect key, fetch the
signed transaction info, and read the decoded payload (productId, expiresDate,
originalTransactionId, environment).

Requires: APPLE_IAP_BUNDLE_ID, APPLE_IAP_ISSUER_ID, APPLE_IAP_KEY_ID,
APPLE_IAP_PRIVATE_KEY (PEM of the .p8). Without them, construction raises and the
factory falls back to the mock verifier.

NOTE: the JWS is fetched directly from Apple's authenticated TLS endpoint and is
Apple-signed; full x5c certificate-chain verification of the JWS is a hardening
follow-up (see docs/BILLING.md).
"""
from __future__ import annotations

import base64
import json
import logging
import time
from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.models.enums import BillingProvider
from app.services.billing.iap.base import PurchaseVerification
from app.services.billing.iap.products import plan_for_product

logger = logging.getLogger(__name__)

_PROD_BASE = "https://api.storekit.itunes.apple.com"
_SANDBOX_BASE = "https://api.storekit-sandbox.itunes.apple.com"


class AppleVerifier:
    provider = BillingProvider.APPLE

    def __init__(self) -> None:
        missing = [
            name
            for name, val in (
                ("APPLE_IAP_BUNDLE_ID", settings.APPLE_IAP_BUNDLE_ID),
                ("APPLE_IAP_ISSUER_ID", settings.APPLE_IAP_ISSUER_ID),
                ("APPLE_IAP_KEY_ID", settings.APPLE_IAP_KEY_ID),
                ("APPLE_IAP_PRIVATE_KEY", settings.APPLE_IAP_PRIVATE_KEY),
            )
            if not val
        ]
        if missing:
            raise RuntimeError(f"Apple IAP not configured: {', '.join(missing)}")
        self._base = (
            _SANDBOX_BASE
            if settings.APPLE_IAP_ENVIRONMENT.lower() == "sandbox"
            else _PROD_BASE
        )

    def _signed_jwt(self) -> str:
        import jwt  # pyjwt

        now = int(time.time())
        return jwt.encode(
            {
                "iss": settings.APPLE_IAP_ISSUER_ID,
                "iat": now,
                "exp": now + 600,
                "aud": "appstoreconnect-v1",
                "bid": settings.APPLE_IAP_BUNDLE_ID,
            },
            settings.APPLE_IAP_PRIVATE_KEY,
            algorithm="ES256",
            headers={"kid": settings.APPLE_IAP_KEY_ID, "typ": "JWT"},
        )

    def verify(self, *, product_id: str, token: str) -> PurchaseVerification:
        try:
            resp = httpx.get(
                f"{self._base}/inApps/v1/transactions/{token}",
                headers={"Authorization": f"Bearer {self._signed_jwt()}"},
                timeout=15.0,
            )
            resp.raise_for_status()
            signed = resp.json().get("signedTransactionInfo", "")
            payload = _decode_jws_payload(signed)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[apple-iap] verify failed: %s", exc)
            return PurchaseVerification(
                valid=False, provider=self.provider, product_id=product_id,
                error="Verificarea Apple a eșuat.",
            )

        got_product = payload.get("productId", product_id)
        plan = plan_for_product(got_product)
        expires_ms = payload.get("expiresDate")
        expires_at = (
            datetime.fromtimestamp(expires_ms / 1000, tz=UTC)
            if isinstance(expires_ms, (int, float))
            else None
        )
        revoked = payload.get("revocationDate") is not None
        return PurchaseVerification(
            valid=plan is not None and not revoked,
            provider=self.provider,
            product_id=got_product,
            plan=plan,
            transaction_id=str(
                payload.get("originalTransactionId") or payload.get("transactionId") or ""
            )
            or None,
            expires_at=expires_at,
            environment=str(payload.get("environment", "Production")).lower(),
            auto_renewing=True,
            raw=payload,
            error=None if plan is not None else f"Produs necunoscut: {got_product}",
        )


def _decode_jws_payload(jws: str) -> dict:
    """Decode the (middle) payload segment of a compact JWS without verifying."""
    parts = jws.split(".")
    if len(parts) != 3:
        raise ValueError("JWS malformat")
    padded = parts[1] + "=" * (-len(parts[1]) % 4)
    return json.loads(base64.urlsafe_b64decode(padded))
