"""In-App Purchase endpoints: purchase verification + store server webhooks.

`/verify` is called by the mobile app after a native StoreKit / Play Billing
purchase; the backend validates the receipt with the store and updates the
subscription. The webhook endpoints receive store server notifications
(renewals, cancellations, refunds) and keep the subscription in sync.
"""
from __future__ import annotations

import base64
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import BillingProvider
from app.models.user import User
from app.schemas.billing import IapVerifyRequest, SubscriptionOut
from app.services.billing import entitlements, iap
from app.services.billing.iap.apple import _decode_jws_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing/iap", tags=["billing-iap"])


def _subscription_out(user: User) -> SubscriptionOut:
    from app.models.enums import SubscriptionStatus

    plan = entitlements.effective_plan(user)
    info = entitlements.plan_info(plan)
    sub = user.subscription
    return SubscriptionOut(
        plan=plan,
        plan_name=info.name,
        status=sub.status if sub else SubscriptionStatus.ACTIVE,
        provider=sub.provider if sub else BillingProvider.NONE,
        current_period_end=sub.current_period_end if sub else None,
        trial_end=sub.trial_end if sub else None,
        cancel_at_period_end=sub.cancel_at_period_end if sub else False,
        limits=info.limits,
        flags=info.flags,
    )


@router.post("/verify", response_model=SubscriptionOut)
def verify_purchase(
    payload: IapVerifyRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    if payload.platform not in (BillingProvider.APPLE, BillingProvider.GOOGLE):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Platformă invalidă (apple sau google).",
        )
    verifier = iap.get_verifier(payload.platform)
    result = verifier.verify(product_id=payload.product_id, token=payload.token)
    if not result.valid:
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            result.error or "Achiziția nu a putut fi validată.",
        )
    iap.service.apply_verification(db, user, result)
    db.refresh(user)
    return _subscription_out(user)


# --------------------------------------------------------------------------
# Store server notifications (renewals / cancellations / refunds)
# --------------------------------------------------------------------------
def _sync_from_verification(db: Session, result) -> None:
    """Apply a verification to the subscription owning its transaction id."""
    if not result.transaction_id:
        return
    sub = iap.service.find_by_transaction(db, result.transaction_id)
    if sub is None:
        logger.info("[iap-webhook] no subscription for txn %s", result.transaction_id)
        return
    iap.service.apply_verification(db, sub.user, result)


@router.post("/apple/notifications")
async def apple_notifications(request: Request, db: Session = Depends(get_db)) -> dict:
    """App Store Server Notifications V2 (signed JWS envelope).

    Returns 200 even on parse issues so Apple does not retry-storm; failures are
    logged. Full x5c signature verification is a hardening follow-up.
    """
    try:
        body = await request.json()
        payload = _decode_jws_payload(body["signedPayload"])
        txn = _decode_jws_payload(payload["data"]["signedTransactionInfo"])
        verification = _apple_txn_to_verification(txn, payload.get("notificationType"))
        _sync_from_verification(db, verification)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[apple-iap] notification error: %s", exc)
    return {"status": "ok"}


@router.post("/google/notifications")
async def google_notifications(request: Request, db: Session = Depends(get_db)) -> dict:
    """Google Real-time Developer Notifications (Pub/Sub push envelope)."""
    try:
        body = await request.json()
        data = json.loads(base64.b64decode(body["message"]["data"]))
        sub_notif = data.get("subscriptionNotification")
        if sub_notif:
            verifier = iap.get_verifier(BillingProvider.GOOGLE)
            result = verifier.verify(
                product_id=sub_notif["subscriptionId"],
                token=sub_notif["purchaseToken"],
            )
            _sync_from_verification(db, result)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[google-iap] notification error: %s", exc)
    return {"status": "ok"}


def _apple_txn_to_verification(txn: dict, notification_type: str | None):
    """Build a PurchaseVerification from a decoded Apple transaction payload."""
    from datetime import UTC, datetime

    from app.services.billing.iap.base import PurchaseVerification
    from app.services.billing.iap.products import plan_for_product

    product_id = txn.get("productId", "")
    plan = plan_for_product(product_id)
    expires_ms = txn.get("expiresDate")
    expires_at = (
        datetime.fromtimestamp(expires_ms / 1000, tz=UTC)
        if isinstance(expires_ms, (int, float))
        else None
    )
    revoked = txn.get("revocationDate") is not None or notification_type in (
        "REFUND",
        "REVOKE",
    )
    return PurchaseVerification(
        valid=plan is not None and not revoked,
        provider=BillingProvider.APPLE,
        product_id=product_id,
        plan=plan,
        transaction_id=str(txn.get("originalTransactionId") or "") or None,
        expires_at=expires_at,
        environment=str(txn.get("environment", "Production")).lower(),
        raw=txn,
    )
