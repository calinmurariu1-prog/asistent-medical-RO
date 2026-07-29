"""Module 1 - Authentication endpoints."""
from __future__ import annotations

import jwt
import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import (
    EmailVerifyRequest,
    LoginRequest,
    MFAActivateRequest,
    MFASetupResponse,
    PasswordResetConfirm,
    PasswordResetRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.services import audit
from app.services.token_service import (
    EMAIL_VERIFY,
    PASSWORD_RESET,
    create_purpose_token,
    verify_purpose_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(
    payload: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    if db.scalar(select(User).where(User.email == payload.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.PATIENT,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # In production, email this verification token instead of discarding it.
    create_purpose_token(str(user.id), EMAIL_VERIFY)
    audit.record(db, user_id=user.id, action="register", ip_address=_client_ip(request))
    return user


@router.post("/login", response_model=TokenPair)
def login(
    payload: LoginRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenPair:
    user = db.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or not user.hashed_password
        or not verify_password(payload.password, user.hashed_password)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account disabled")

    if user.mfa_enabled:
        if not payload.mfa_code:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MFA code required")
        if not pyotp.TOTP(user.mfa_secret).verify(payload.mfa_code, valid_window=1):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")

    audit.record(db, user_id=user.id, action="login", ip_address=_client_ip(request))
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest) -> TokenPair:
    try:
        data = decode_token(payload.refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from None
    if data.get("type") != REFRESH:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")
    sub = data["sub"]
    return TokenPair(
        access_token=create_access_token(sub),
        refresh_token=create_refresh_token(sub),
    )


@router.post("/password-reset/request")
def password_reset_request(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == payload.email))
    if user:
        create_purpose_token(str(user.id), PASSWORD_RESET, hours=2)
        # TODO: email the token to the user.
    # Always 200 to prevent account enumeration.
    return {"detail": "If the email exists, a reset link has been sent."}


@router.post("/password-reset/confirm")
def password_reset_confirm(
    payload: PasswordResetConfirm, db: Session = Depends(get_db)
) -> dict[str, str]:
    sub = verify_purpose_token(payload.token, PASSWORD_RESET)
    if sub is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")
    user = db.get(User, int(sub))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"detail": "Password updated"}


@router.post("/email/verify")
def verify_email(
    payload: EmailVerifyRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    sub = verify_purpose_token(payload.token, EMAIL_VERIFY)
    if sub is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid or expired token")
    user = db.get(User, int(sub))
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    user.is_email_verified = True
    db.commit()
    return {"detail": "Email verified"}


@router.post("/mfa/setup", response_model=MFASetupResponse)
def mfa_setup(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MFASetupResponse:
    secret = pyotp.random_base32()
    current.mfa_secret = secret
    db.add(current)
    db.commit()
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current.email, issuer_name=settings.PROJECT_NAME
    )
    return MFASetupResponse(secret=secret, otpauth_uri=uri)


@router.post("/mfa/activate")
def mfa_activate(
    payload: MFAActivateRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    if not current.mfa_secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Run /mfa/setup first")
    if not pyotp.TOTP(current.mfa_secret).verify(payload.code, valid_window=1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code")
    current.mfa_enabled = True
    db.add(current)
    db.commit()
    return {"detail": "MFA enabled"}


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)) -> User:
    return current


@router.post("/login-form", response_model=TokenPair, include_in_schema=False)
def login_form(
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenPair:
    """OAuth2 password flow used by the Swagger 'Authorize' button."""
    user = db.scalar(select(User).where(User.email == form.username))
    if (
        user is None
        or not user.hashed_password
        or not verify_password(form.password, user.hashed_password)
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    return TokenPair(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )
