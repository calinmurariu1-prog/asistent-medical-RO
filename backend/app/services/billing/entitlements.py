"""Plan catalog + entitlements: what each subscription plan unlocks.

The catalog is the single source of truth for pricing and per-plan limits/flags.
`-1` means unlimited. Feature gating elsewhere in the app reads these values via
`get_entitlements(user)` so limits live in one place.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.models.enums import SubscriptionPlan, SubscriptionStatus
from app.models.subscription import Subscription
from app.models.user import User

UNLIMITED = -1


@dataclass(frozen=True)
class PlanInfo:
    plan: SubscriptionPlan
    name: str
    price_eur_month: float
    tagline: str
    features: list[str]
    limits: dict[str, int] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)


# Limit keys used across the app.
LIMIT_DOCUMENTS = "documents"
LIMIT_AI_MESSAGES_MONTH = "ai_messages_per_month"
LIMIT_HEALTH_SOURCES = "health_sources"
LIMIT_FAMILY_MEMBERS = "family_members"

# Flag keys.
FLAG_ADVANCED_AI = "advanced_ai"        # record summary / analyte comparison
FLAG_EXPORT = "export"                   # PDF/DOCX medical export
FLAG_PRIORITY_SUPPORT = "priority_support"


_CATALOG: dict[SubscriptionPlan, PlanInfo] = {
    SubscriptionPlan.FREE: PlanInfo(
        plan=SubscriptionPlan.FREE,
        name="Gratuit",
        price_eur_month=0.0,
        tagline="Esențialul dosarului tău medical.",
        features=[
            "Până la 20 de documente",
            "30 de mesaje AI pe lună",
            "O sursă de sănătate conectată",
            "Analize explicate",
        ],
        limits={
            LIMIT_DOCUMENTS: 20,
            LIMIT_AI_MESSAGES_MONTH: 30,
            LIMIT_HEALTH_SOURCES: 1,
            LIMIT_FAMILY_MEMBERS: 0,
        },
        flags={
            FLAG_ADVANCED_AI: False,
            FLAG_EXPORT: False,
            FLAG_PRIORITY_SUPPORT: False,
        },
    ),
    SubscriptionPlan.PREMIUM: PlanInfo(
        plan=SubscriptionPlan.PREMIUM,
        name="Premium",
        price_eur_month=6.99,
        tagline="Fără limite, cu AI avansat și export.",
        features=[
            "Documente nelimitate",
            "Mesaje AI nelimitate",
            "Toate sursele de sănătate (Apple/Google/Huawei)",
            "AI avansat: rezumat dosar, comparații în timp",
            "Export medical (PDF/DOCX)",
            "Suport prioritar",
        ],
        limits={
            LIMIT_DOCUMENTS: UNLIMITED,
            LIMIT_AI_MESSAGES_MONTH: UNLIMITED,
            LIMIT_HEALTH_SOURCES: UNLIMITED,
            LIMIT_FAMILY_MEMBERS: 0,
        },
        flags={
            FLAG_ADVANCED_AI: True,
            FLAG_EXPORT: True,
            FLAG_PRIORITY_SUPPORT: True,
        },
    ),
    SubscriptionPlan.FAMILY: PlanInfo(
        plan=SubscriptionPlan.FAMILY,
        name="Familie",
        price_eur_month=12.99,
        tagline="Premium pentru toată familia (până la 5 membri).",
        features=[
            "Tot ce include Premium",
            "Până la 5 membri de familie",
            "Dosar partajat controlat",
        ],
        limits={
            LIMIT_DOCUMENTS: UNLIMITED,
            LIMIT_AI_MESSAGES_MONTH: UNLIMITED,
            LIMIT_HEALTH_SOURCES: UNLIMITED,
            LIMIT_FAMILY_MEMBERS: 5,
        },
        flags={
            FLAG_ADVANCED_AI: True,
            FLAG_EXPORT: True,
            FLAG_PRIORITY_SUPPORT: True,
        },
    ),
}

# Statuses that grant access to the paid plan's entitlements.
_ACTIVE_STATUSES = {SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING}


def plan_catalog() -> list[PlanInfo]:
    return list(_CATALOG.values())


def plan_info(plan: SubscriptionPlan) -> PlanInfo:
    return _CATALOG[plan]


def _is_current(sub: Subscription) -> bool:
    """A subscription grants its plan only while active/trialing and unexpired."""
    if sub.status not in _ACTIVE_STATUSES:
        return False
    if sub.current_period_end is not None:
        end = sub.current_period_end
        if end.tzinfo is None:
            end = end.replace(tzinfo=UTC)
        if end < datetime.now(UTC):
            return False
    return True


def effective_plan(user: User) -> SubscriptionPlan:
    """Resolve the plan a user is actually entitled to right now."""
    sub = getattr(user, "subscription", None)
    if sub is None or not _is_current(sub):
        return SubscriptionPlan.FREE
    return sub.plan


def get_entitlements(user: User) -> dict:
    plan = effective_plan(user)
    info = _CATALOG[plan]
    return {
        "plan": plan.value,
        "plan_name": info.name,
        "limits": dict(info.limits),
        "flags": dict(info.flags),
    }


def limit_for(user: User, key: str) -> int:
    """Numeric limit for a feature (`UNLIMITED` = -1 means no cap)."""
    return _CATALOG[effective_plan(user)].limits.get(key, 0)


def has_flag(user: User, key: str) -> bool:
    return _CATALOG[effective_plan(user)].flags.get(key, False)


def within_limit(user: User, key: str, current_count: int) -> bool:
    """True if creating one more item stays within the plan's limit."""
    cap = limit_for(user, key)
    if cap == UNLIMITED:
        return True
    return current_count < cap
