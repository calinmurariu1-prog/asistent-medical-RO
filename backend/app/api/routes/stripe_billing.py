"""Stripe web-subscription endpoints: Checkout, Billing Portal, webhook."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import SubscriptionPlan
from app.models.user import User
from app.schemas.billing import CheckoutRequest, CheckoutResponse
from app.services.billing import stripe_pay

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing/stripe", tags=["billing-stripe"])


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    payload: CheckoutRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    if payload.plan == SubscriptionPlan.FREE:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Planul gratuit nu necesită plată.",
        )
    try:
        url = stripe_pay.gateway.create_checkout_session(db, user, payload.plan)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return CheckoutResponse(url=url)


@router.post("/portal", response_model=CheckoutResponse)
def create_portal(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CheckoutResponse:
    try:
        url = stripe_pay.gateway.create_portal_session(db, user)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc)) from exc
    return CheckoutResponse(url=url)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> dict:
    payload = await request.body()
    try:
        event = stripe_pay.webhooks.construct_event(payload, stripe_signature)
    except Exception as exc:  # noqa: BLE001  (bad signature / malformed)
        logger.warning("[stripe] webhook rejected: %s", exc)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Webhook invalid") from exc

    try:
        stripe_pay.webhooks.handle_event(db, event)
    except Exception as exc:  # noqa: BLE001
        logger.exception("[stripe] webhook handling failed: %s", exc)
        # 200 so Stripe doesn't retry-storm on a transient handler bug.
    return {"status": "ok"}
