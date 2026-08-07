"""Google Play verifier (Play Developer API).

Flow: the app sends the purchase token + product (subscription) ID. We obtain an
OAuth2 access token via the service-account (JWT-bearer grant), then call
`purchases.subscriptions.get` and read expiryTimeMillis / paymentState.

Requires: GOOGLE_PLAY_PACKAGE_NAME, GOOGLE_PLAY_SERVICE_ACCOUNT_JSON. Without
them, construction raises and the factory falls back to the mock verifier.
"""
from __future__ import annotations

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

_SCOPE = "https://www.googleapis.com/auth/androidpublisher"
_API = "https://androidpublisher.googleapis.com/androidpublisher/v3"


class GoogleVerifier:
    provider = BillingProvider.GOOGLE

    def __init__(self) -> None:
        if not settings.GOOGLE_PLAY_PACKAGE_NAME or not settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON:
            raise RuntimeError("Google Play IAP not configured")
        try:
            self._sa = json.loads(settings.GOOGLE_PLAY_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON invalid") from exc
        self._package = settings.GOOGLE_PLAY_PACKAGE_NAME

    def _access_token(self) -> str:
        import jwt  # pyjwt

        now = int(time.time())
        token_uri = self._sa.get("token_uri", "https://oauth2.googleapis.com/token")
        assertion = jwt.encode(
            {
                "iss": self._sa["client_email"],
                "scope": _SCOPE,
                "aud": token_uri,
                "iat": now,
                "exp": now + 3600,
            },
            self._sa["private_key"],
            algorithm="RS256",
        )
        resp = httpx.post(
            token_uri,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def verify(self, *, product_id: str, token: str) -> PurchaseVerification:
        try:
            access = self._access_token()
            url = (
                f"{_API}/applications/{self._package}"
                f"/purchases/subscriptions/{product_id}/tokens/{token}"
            )
            resp = httpx.get(
                url, headers={"Authorization": f"Bearer {access}"}, timeout=15.0
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("[google-iap] verify failed: %s", exc)
            return PurchaseVerification(
                valid=False, provider=self.provider, product_id=product_id,
                error="Verificarea Google Play a eșuat.",
            )

        plan = plan_for_product(product_id)
        expiry_ms = data.get("expiryTimeMillis")
        expires_at = (
            datetime.fromtimestamp(int(expiry_ms) / 1000, tz=UTC)
            if expiry_ms is not None
            else None
        )
        # paymentState: 0 pending, 1 received, 2 free trial, 3 deferred.
        payment_state = data.get("paymentState")
        paid = payment_state in (1, 2)
        return PurchaseVerification(
            valid=plan is not None and paid,
            provider=self.provider,
            product_id=product_id,
            plan=plan,
            transaction_id=str(data.get("orderId") or "") or None,
            expires_at=expires_at,
            environment="production",
            auto_renewing=bool(data.get("autoRenewing", True)),
            raw=data,
            error=None if plan is not None else f"Produs necunoscut: {product_id}",
        )
