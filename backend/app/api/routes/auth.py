"""Module 1 - Authentication endpoints."""
from __future__ import annotations

import jwt
import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.browser_session import (
    REFRESH_COOKIE,
    clear_browser_cookies,
    require_browser_origin,
    set_browser_cookies,
)
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import RateLimiter
from app.core.security import (
    REFRESH,
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_field,
    encrypt_field,
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
from app.services.email import send_password_reset_email, send_verification_email
from app.services.token_service import (
    EMAIL_VERIFY,
    PASSWORD_RESET,
    consume_purpose_token,
    create_purpose_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

# Brute-force protection on credential endpoints.
_auth_limiter = RateLimiter(
    settings.RATE_LIMIT_LOGIN_TIMES, settings.RATE_LIMIT_WINDOW_SECONDS
)


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.post(
    "/register",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_auth_limiter)],
)
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

    token = create_purpose_token(str(user.id), EMAIL_VERIFY, db=db)
    db.commit()
    send_verification_email(user.email, token)
    audit.record(db, user_id=user.id, action="register", ip_address=_client_ip(request))
    return user


@router.post(
    "/login", response_model=TokenPair, dependencies=[Depends(_auth_limiter)]
)
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
        secret = decrypt_field(user.mfa_secret)
        if not secret or not pyotp.TOTP(secret).verify(payload.mfa_code, valid_window=1):
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid MFA code")

    audit.record(db, user_id=user.id, action="login", ip_address=_client_ip(request))
    return TokenPair(
        access_token=create_access_token(str(user.id), user.token_version),
        refresh_token=create_refresh_token(str(user.id), user.token_version),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        data = decode_token(payload.refresh_token)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid refresh token") from None
    if data.get("type") != REFRESH:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token type")

    user = db.get(User, int(data["sub"]))
    if user is None or not user.is_active or data.get("ver", 0) != user.token_version:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token revoked")

    return TokenPair(
        access_token=create_access_token(str(user.id), user.token_version),
        refresh_token=create_refresh_token(str(user.id), user.token_version),
    )


@router.post("/password-reset/request", dependencies=[Depends(_auth_limiter)])
def password_reset_request(
    payload: PasswordResetRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    if settings.is_production and not settings.SMTP_HOST:
        raise HTTPException(503, "Recuperarea parolei este temporar indisponibilă.")
    user = db.scalar(select(User).where(User.email == payload.email))
    if user and user.is_active:
        token = create_purpose_token(str(user.id), PASSWORD_RESET, hours=2, db=db)
        db.commit()
        send_password_reset_email(user.email, token)
    # Always 200 to prevent account enumeration.
    return {"detail": "If the email exists, a reset link has been sent."}


@router.post("/password-reset/confirm")
def password_reset_confirm(
    payload: PasswordResetConfirm, db: Session = Depends(get_db)
) -> dict[str, str]:
    user = consume_purpose_token(payload.token, PASSWORD_RESET, db)
    if user is None:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link invalid, expirat sau deja folosit.")
    user.hashed_password = hash_password(payload.new_password)
    # Invalidate all existing sessions after a password reset.
    user.token_version += 1
    from datetime import UTC, datetime

    from sqlalchemy import update

    from app.models.user import RecoveryToken
    db.execute(update(RecoveryToken).where(
        RecoveryToken.user_id == user.id, RecoveryToken.purpose == PASSWORD_RESET,
        RecoveryToken.consumed_at.is_(None)).values(consumed_at=datetime.now(UTC)))
    db.commit()
    return {"detail": "Password updated"}


@router.post("/email/verify")
def verify_email(
    payload: EmailVerifyRequest, db: Session = Depends(get_db)
) -> dict[str, str]:
    user = consume_purpose_token(payload.token, EMAIL_VERIFY, db)
    if user is None:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link invalid, expirat sau deja folosit.")
    user.is_email_verified = True
    db.commit()
    return {"detail": "Email verified"}


@router.post("/mfa/setup", response_model=MFASetupResponse,
             dependencies=[Depends(_auth_limiter)])
def mfa_setup(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> MFASetupResponse:
    secret = pyotp.random_base32()
    changed = db.execute(update(User).where(
        User.id == current.id, User.mfa_enabled.is_(False),
    ).values(mfa_secret=encrypt_field(secret)))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "MFA este deja activ. Secretul nu poate fi înlocuit.")
    audit.record(db, user_id=current.id, action="mfa_setup")
    uri = pyotp.totp.TOTP(secret).provisioning_uri(
        name=current.email, issuer_name=settings.PROJECT_NAME
    )
    return MFASetupResponse(secret=secret, otpauth_uri=uri)


@router.post("/mfa/activate", dependencies=[Depends(_auth_limiter)])
def mfa_activate(
    payload: MFAActivateRequest,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    secret = decrypt_field(current.mfa_secret)
    if not secret:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Run /mfa/setup first")
    if not pyotp.TOTP(secret).verify(payload.code, valid_window=1):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid code")
    # Compare the encrypted setup snapshot: a concurrent setup must not enable
    # a secret different from the one whose code was just verified.
    changed = db.execute(update(User).where(
        User.id == current.id, User.mfa_enabled.is_(False),
        User.mfa_secret == current.mfa_secret,
    ).values(mfa_enabled=True, token_version=User.token_version + 1))
    if changed.rowcount != 1:
        db.rollback()
        raise HTTPException(409, "Configurarea MFA s-a schimbat. Reia autentificarea.")
    audit.record(db, user_id=current.id, action="mfa_activate")
    return {"detail": "MFA activat. Autentifică-te din nou cu parola și codul MFA."}


@router.get("/me", response_model=UserOut)
def me(current: User = Depends(get_current_user)) -> User:
    return current


@router.post("/logout-all")
def logout_all(
    current: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> dict[str, str]:
    """Revoke every existing token for this user (all devices)."""
    current.token_version += 1
    db.add(current)
    db.commit()
    return {"detail": "Toate sesiunile au fost deconectate."}


@router.post(
    "/login-form", response_model=TokenPair, include_in_schema=False,
    dependencies=[Depends(_auth_limiter)],
)
def login_form(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenPair:
    """Swagger login applies the same account and MFA checks as JSON login.

    OAuth2's password form cannot supply our TOTP field. MFA users must use
    /login with mfa_code; never issue tokens on the basis of the password alone.
    """
    try:
        payload = LoginRequest(email=form.username, password=form.password)
    except ValidationError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials") from None
    return login(payload, request, db)


@router.post("/browser/login", dependencies=[Depends(_auth_limiter)])
def browser_login(
    payload: LoginRequest, request: Request, response: Response,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    require_browser_origin(request)
    tokens = login(payload, request, db)
    set_browser_cookies(response, tokens.access_token, tokens.refresh_token)
    return {"detail": "Autentificare reușită."}


@router.post("/browser/refresh")
def browser_refresh(
    request: Request, response: Response, db: Session = Depends(get_db),
) -> dict[str, str]:
    require_browser_origin(request)
    token = request.cookies.get(REFRESH_COOKIE)
    if not token:
        raise HTTPException(401, "Sesiune expirată.")
    tokens = refresh(RefreshRequest(refresh_token=token), db)
    set_browser_cookies(response, tokens.access_token, tokens.refresh_token)
    return {"detail": "Sesiune reînnoită."}


@router.post("/browser/logout-all")
def browser_logout_all(
    request: Request, response: Response,
    current: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> dict[str, str]:
    require_browser_origin(request)
    result = logout_all(current, db)
    clear_browser_cookies(response)
    return result


@router.post("/browser/clear")
def browser_clear(request: Request, response: Response) -> dict[str, str]:
    """Clear this browser even when its access token has expired; does not revoke other devices."""
    require_browser_origin(request)
    clear_browser_cookies(response)
    return {"detail": "Cookie-urile acestui browser au fost șterse."}
