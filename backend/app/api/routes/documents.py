"""Module 4 - Document upload, OCR & AI extraction."""
from __future__ import annotations

from datetime import date
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient, require_ai_consent
from app.core.database import get_db
from app.models.document import Document
from app.models.enums import DocumentCategory
from app.models.patient import Patient
from app.schemas.document import (
    DocumentDetailOut,
    DocumentDownloadOut,
    DocumentOut,
)
from app.services import document_processing, ocr
from app.services.ai import get_ai_provider
from app.services.ai.base import AIProvider
from app.services.billing import entitlements
from app.services.billing.entitlements import LIMIT_DOCUMENTS
from app.services.storage import Storage, build_object_key, get_storage

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB
ALLOWED_CONTENT_TYPES = {
    ocr.DOCX_TYPE,
    "application/pdf",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "application/dicom",
    "application/octet-stream",  # some clients send DICOM as octet-stream
}


@router.post("", response_model=DocumentDetailOut, status_code=status.HTTP_201_CREATED,
             dependencies=[Depends(require_ai_consent)])
def upload_document(
    file: UploadFile = File(...),
    category: DocumentCategory = Form(DocumentCategory.OTHER),
    document_date: date | None = Form(None),
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    ai: AIProvider = Depends(get_ai_provider),
) -> Document:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            f"Tip fișier neacceptat: {file.content_type}. "
            "Acceptate: PDF, JPG, PNG, DOCX, DICOM.",
        )

    # Free-plan document quota (Premium/Family are unlimited).
    doc_count = db.scalar(
        select(func.count())
        .select_from(Document)
        .where(Document.patient_id == patient.id)
    )
    if not entitlements.within_limit(patient.user, LIMIT_DOCUMENTS, int(doc_count or 0)):
        raise HTTPException(
            status.HTTP_402_PAYMENT_REQUIRED,
            "Ai atins limita de documente a planului gratuit. "
            "Fă upgrade la Premium pentru documente nelimitate.",
        )

    data = file.file.read(MAX_SIZE_BYTES + 1)
    if len(data) == 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fișier gol")
    if len(data) > MAX_SIZE_BYTES:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"Fișier prea mare (max {MAX_SIZE_BYTES // (1024 * 1024)} MB)",
        )

    if file.content_type == ocr.DOCX_TYPE or (file.filename or "").lower().endswith(".docx"):
        try:
            ocr.validate_docx(data)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from None

    key = build_object_key(patient.id, file.filename or "document")
    storage.put(key, data, file.content_type)

    document = Document(
        patient_id=patient.id,
        category=category,
        original_filename=file.filename or "document",
        content_type=file.content_type,
        size_bytes=len(data),
        storage_key=key,
        document_date=document_date,
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return document_processing.process_document(db, document, storage, ai)


def _owned_document(document_id: int, patient: Patient, db: Session) -> Document:
    document = db.get(Document, document_id)
    if document is None or document.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document inexistent")
    return document


@router.get("", response_model=list[DocumentOut])
def list_documents(
    category: DocumentCategory | None = None,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[Document]:
    stmt = select(Document).where(Document.patient_id == patient.id)
    if category is not None:
        stmt = stmt.where(Document.category == category)
    stmt = stmt.order_by(Document.created_at.desc())
    return list(db.scalars(stmt).all())


@router.get("/{document_id}", response_model=DocumentDetailOut)
def get_document(
    document_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Document:
    return _owned_document(document_id, patient, db)


@router.get("/{document_id}/original")
def original_document(
    document_id: int, patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db), storage: Storage = Depends(get_storage),
) -> Response:
    document = _owned_document(document_id, patient, db)
    try:
        data = storage.get(document.storage_key)
    except FileNotFoundError:
        raise HTTPException(404, "Original indisponibil") from None
    return Response(data, media_type="application/octet-stream", headers={
        "Content-Disposition": ("attachment; filename*=UTF-8''"
                                + quote(document.original_filename, safe="")),
        "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff",
    })


@router.get("/{document_id}/download", response_model=DocumentDownloadOut)
def download_document(
    document_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> DocumentDownloadOut:
    document = _owned_document(document_id, patient, db)
    from app.core.config import settings
    if settings.STORAGE_BACKEND == "local":
        raise HTTPException(409, "Folosește descărcarea autentificată a originalului.")
    url = storage.presigned_url(document.storage_key, expires=3600)
    return DocumentDownloadOut(url=url, expires_in=3600)


@router.post("/{document_id}/reprocess", response_model=DocumentDetailOut,
             dependencies=[Depends(require_ai_consent)])
def reprocess_document(
    document_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    ai: AIProvider = Depends(get_ai_provider),
) -> Document:
    document = _owned_document(document_id, patient, db)
    try:
        return document_processing.process_document(db, document, storage, ai)
    except document_processing.DocumentBusyError:
        raise HTTPException(409, "Documentul este deja în curs de procesare.") from None


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
) -> Response:
    document = _owned_document(document_id, patient, db)
    try:
        storage.delete(document.storage_key)
    except Exception:  # noqa: BLE001  (best-effort; DB row is source of truth)
        pass
    db.delete(document)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
