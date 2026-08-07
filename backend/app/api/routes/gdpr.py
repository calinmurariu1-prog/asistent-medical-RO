"""GDPR endpoints: data export, account deletion, consent management."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import verify_password
from app.models.user import Consent, User
from app.schemas.gdpr import ConsentIn, ConsentOut, DeleteAccountRequest
from app.services import audit, gdpr

router = APIRouter(prefix="/gdpr", tags=["gdpr"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/export")
def export_my_data(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Right of access & portability (GDPR Art. 15/20): full data export."""
    audit.record(db, user_id=user.id, action="gdpr_export", ip_address=_client_ip(request))
    return gdpr.export_user_data(db, user)


@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    payload: DeleteAccountRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    """Right to erasure (GDPR Art. 17). Requires password + explicit confirm."""
    if not payload.confirm:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Confirmarea este necesară.")
    if not user.hashed_password or not verify_password(
        payload.password, user.hashed_password
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Parolă incorectă.")
    # Audit BEFORE deletion (audit_logs.user_id is SET NULL, so the record survives).
    audit.record(
        db,
        user_id=user.id,
        action="gdpr_delete_account",
        ip_address=_client_ip(request),
    )
    gdpr.delete_user(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/consents", response_model=list[ConsentOut])
def my_consents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ConsentOut]:
    """Latest state per consent type."""
    rows = db.scalars(
        select(Consent)
        .where(Consent.user_id == user.id)
        .order_by(Consent.id.desc())
    ).all()
    latest: dict = {}
    for c in rows:
        latest.setdefault(c.consent_type, c)
    return [ConsentOut.model_validate(c) for c in latest.values()]


@router.post("/consents", response_model=ConsentOut, status_code=status.HTTP_201_CREATED)
def set_consent(
    payload: ConsentIn,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Consent:
    """Record a consent grant or revocation (append-only history)."""
    consent = Consent(
        user_id=user.id,
        consent_type=payload.consent_type,
        granted=payload.granted,
        ip_address=_client_ip(request),
    )
    db.add(consent)
    audit.record(
        db,
        user_id=user.id,
        action="consent_grant" if payload.granted else "consent_revoke",
        resource_type="consent",
        resource_id=payload.consent_type.value,
        ip_address=_client_ip(request),
    )
    db.refresh(consent)
    return consent
