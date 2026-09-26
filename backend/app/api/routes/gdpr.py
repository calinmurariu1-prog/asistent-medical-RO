"""GDPR endpoints: data export, account deletion, consent management."""
from __future__ import annotations

import pyotp
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import ai_consent_version, get_current_user
from app.core.browser_session import clear_browser_cookies
from app.core.database import get_db
from app.core.rate_limit import RateLimiter
from app.core.security import decrypt_field, verify_password
from app.models.enums import ConsentType
from app.models.patient import Patient
from app.models.user import Consent, User
from app.schemas.gdpr import ConsentIn, ConsentOut, DeleteAccountRequest, SensitiveExportRequest
from app.services import audit, gdpr, mfa_recovery, record_archive, storage_cleanup
from app.services.ai import get_ai_provider
from app.services.ai.base import AIProvider
from app.services.storage import Storage, get_storage

router = APIRouter(prefix="/gdpr", tags=["gdpr"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/export")
def export_my_data(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Account and clinical export; omitted sections are disclosed in metadata."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    audit.record(db, user_id=user.id, action="gdpr_export", ip_address=_client_ip(request))
    return gdpr.export_user_data(db, user)


@router.post("/export/with-identifier", dependencies=[Depends(RateLimiter(5, 60))])
def export_with_identifier(
    payload: SensitiveExportRequest, user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not payload.include_cnp:
        raise HTTPException(400, "Confirmă includerea CNP în export.")
    version = user.token_version
    account = db.scalar(select(User).where(User.id == user.id).with_for_update()
                        .execution_options(populate_existing=True))
    if account is None or not account.is_active or account.token_version != version:
        raise HTTPException(401, "Sesiune expirată.")
    if not account.hashed_password or not verify_password(
        payload.password, account.hashed_password
    ):
        raise HTTPException(400, "Parolă sau cod MFA incorect.")
    if account.mfa_enabled:
        secret = decrypt_field(account.mfa_secret)
        if not payload.mfa_code or not secret:
            raise HTTPException(400, "Parolă sau cod MFA incorect.")
        if not pyotp.TOTP(secret).verify(payload.mfa_code, valid_window=1):
            if not mfa_recovery.consume(db, account.id, payload.mfa_code):
                db.rollback()
                raise HTTPException(400, "Parolă sau cod MFA incorect.")
    patient = db.scalar(select(Patient).where(Patient.user_id == account.id))
    identifier = decrypt_field(patient.cnp_encrypted) if patient else None
    if patient and patient.cnp_encrypted and identifier is None:
        db.rollback()
        raise HTTPException(503, "Identificatorul nu a putut fi exportat. Reîncearcă.")
    data = gdpr.export_user_data(db, account)
    data["export_metadata"]["not_included"].remove("cnp")
    data["export_metadata"]["cnp_requested"] = True
    if data["patient"] is not None:
        data["patient"]["cnp"] = identifier
    audit.record(db, user_id=account.id, action="gdpr_export_with_identifier")
    return data


@router.get("/export/archive", dependencies=[Depends(RateLimiter(2, 60))])
def export_archive(
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> Response:
    try:
        content = record_archive.build(db, user, storage)
    except record_archive.ArchiveTooLarge:
        raise HTTPException(413, "Arhiva depășește 25 MB sau 1000 de documente. "
                            "Descarcă JSON și originalele separat.",
                            headers={"Cache-Control": "no-store"}) from None
    except Exception:  # noqa: BLE001 (no partial archive or private provider details)
        raise HTTPException(503, "Arhiva nu a putut fi pregătită complet. "
                            "Un original poate fi indisponibil. Reîncearcă.",
                            headers={"Cache-Control": "no-store"}) from None
    audit.record(db, user_id=user.id, action="gdpr_archive_export")
    return Response(content, media_type="application/zip", headers={
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
        "Content-Disposition": 'attachment; filename="dosar-medical.zip"',
    })


@router.post("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_account(
    payload: DeleteAccountRequest,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
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
    jobs = gdpr.delete_user(db, user)
    try:
        storage_cleanup.process_pending(db, storage, jobs)
        complete = storage_cleanup.pending_count(db, jobs) == 0
    except Exception:  # noqa: BLE001 (durable queue remains available to the worker)
        db.rollback()
        complete = False
    response = (Response(status_code=204) if complete else JSONResponse(status_code=202, content={
        "cleanup_pending": True,
        "detail": "Contul a fost șters. Ștergerea originalelor este în curs și va fi reîncercată.",
    }))
    clear_browser_cookies(response)
    return response


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
    ai: AIProvider = Depends(get_ai_provider),
) -> Consent:
    """Record a consent grant or revocation (append-only history)."""
    version = "1.0"
    if payload.consent_type == ConsentType.AI_PROCESSING:
        if payload.granted and ai.name != "mock" and payload.provider != ai.name:
            raise HTTPException(
                409, "Furnizorul AI s-a schimbat. Reîncarcă setările înainte de acord.")
        version = ai_consent_version(ai)
    consent = Consent(
        version=version,
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
