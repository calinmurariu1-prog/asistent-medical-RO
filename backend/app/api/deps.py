"""Shared FastAPI dependencies: DB session and authenticated user."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.browser_session import ACCESS_COOKIE, require_browser_origin
from app.core.config import settings
from app.core.database import get_db
from app.core.security import ACCESS, decode_token
from app.models.enums import ConsentType, UserRole
from app.models.patient import Patient
from app.models.user import Consent, User
from app.services.ai import get_ai_provider
from app.services.ai.base import AIProvider

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login-form", auto_error=False)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        token = request.cookies.get(ACCESS_COOKIE)
        if token and request.method not in {"GET", "HEAD", "OPTIONS"}:
            require_browser_origin(request)
    if not token:
        raise _CREDENTIALS_EXC
    try:
        payload = decode_token(token)
    except jwt.PyJWTError as exc:  # noqa: F841
        raise _CREDENTIALS_EXC from None

    if payload.get("type") != ACCESS:
        raise _CREDENTIALS_EXC

    user_id = payload.get("sub")
    if user_id is None:
        raise _CREDENTIALS_EXC

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise _CREDENTIALS_EXC
    # Token revocation: a bumped token_version invalidates old tokens.
    if payload.get("ver", 0) != user.token_version:
        raise _CREDENTIALS_EXC
    return user


def get_current_patient(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Patient:
    """Return the patient profile for the current user, creating it lazily.

    Queries by user_id (not the cached `user.patient` relationship) and handles
    the unique-constraint race where two concurrent requests both try to create
    the profile.
    """
    patient = db.scalar(select(Patient).where(Patient.user_id == user.id))
    if patient is not None:
        return patient

    patient = Patient(user_id=user.id)
    db.add(patient)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        patient = db.scalar(select(Patient).where(Patient.user_id == user.id))
        if patient is None:
            raise
        return patient
    db.refresh(patient)
    return patient


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return user


def require_feature(flag: str):
    """Dependency factory: gate an endpoint behind a plan feature flag.

    Returns 402 Payment Required when the current user's effective plan does not
    include the flag. Used to gate premium-only capabilities.
    """
    from app.services.billing import entitlements

    def _dep(user: User = Depends(get_current_user)) -> User:
        if not entitlements.has_flag(user, flag):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Această funcție este disponibilă în planul Premium.",
            )
        return user

    return _dep


def require_ai_consent(
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai_provider),
) -> None:
    """Every external provider requires current consent, regardless of feature flags."""
    if not settings.REQUIRE_AI_CONSENT and ai.name == "mock":
        return
    latest = db.scalar(
        select(Consent)
        .where(
            Consent.user_id == user.id,
            Consent.consent_type == ConsentType.AI_PROCESSING,
        )
        .order_by(Consent.id.desc())
    )
    if latest is None or not latest.granted or latest.version != ai_consent_version(ai):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este necesar acordul pentru furnizorul AI curent. Îl poți gestiona în Setări.",
        )


def ai_consent_version(ai: AIProvider) -> str:
    return f"ai-v2:{ai.name}"
