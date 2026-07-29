"""Shared FastAPI dependencies: DB session and authenticated user."""
from __future__ import annotations

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import ACCESS, decode_token
from app.models.enums import UserRole
from app.models.patient import Patient
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login-form", auto_error=True)

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
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
    return user


def get_current_patient(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Patient:
    """Return the patient profile for the current user, creating it lazily."""
    patient = user.patient
    if patient is None:
        patient = Patient(user_id=user.id)
        db.add(patient)
        db.commit()
        db.refresh(patient)
    return patient


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return user
