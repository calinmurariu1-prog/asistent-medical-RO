"""SaaS subscription endpoints: plan catalog, current subscription, plan change.

Real payment flows (Stripe Checkout on web, In-App Purchase on mobile) are added
later. For now `change_plan` records the plan directly (provider = manual) so the
product and its feature gating can be built and tested end-to-end.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.enums import BillingProvider, SubscriptionStatus
from app.models.user import User
from app.schemas.billing import ChangePlanRequest, PlanOut, SubscriptionOut
from app.services.billing import entitlements, service

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanOut])
def list_plans() -> list[PlanOut]:
    return [
        PlanOut(
            plan=p.plan,
            name=p.name,
            price_eur_month=p.price_eur_month,
            tagline=p.tagline,
            features=p.features,
            limits=p.limits,
            flags=p.flags,
        )
        for p in entitlements.plan_catalog()
    ]


def _subscription_out(user: User) -> SubscriptionOut:
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


@router.get("/subscription", response_model=SubscriptionOut)
def get_subscription(
    user: User = Depends(get_current_user),
) -> SubscriptionOut:
    return _subscription_out(user)


@router.post("/subscription", response_model=SubscriptionOut)
def change_plan(
    payload: ChangePlanRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SubscriptionOut:
    """Change the current plan.

    NOTE: interim implementation — records the plan without charging. Paid plans
    will be gated behind Stripe Checkout / In-App Purchase before launch.
    """
    service.set_plan(db, user, payload.plan, status=SubscriptionStatus.ACTIVE)
    db.refresh(user)
    return _subscription_out(user)
