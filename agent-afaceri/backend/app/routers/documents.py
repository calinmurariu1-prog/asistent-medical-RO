"""Rute pentru documente salvate + export PDF/DOCX."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import SavedDocument, User
from app.schemas.auth import (
    DocumentCreate,
    DocumentListItem,
    DocumentOut,
    ExportRequest,
)
from app.services.export import to_docx, to_pdf

router = APIRouter(prefix="/documents", tags=["documents"])

_MEDIA = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "document"


def _file_response(title: str, content: str, fmt: str) -> Response:
    fmt = fmt.lower()
    if fmt not in _MEDIA:
        raise HTTPException(status_code=400, detail="Format acceptat: pdf sau docx")
    data = to_pdf(title, content) if fmt == "pdf" else to_docx(title, content)
    filename = f"{_slug(title)}.{fmt}"
    return Response(
        content=data,
        media_type=_MEDIA[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("", response_model=DocumentOut, status_code=201)
def create_document(
    req: DocumentCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedDocument:
    doc = SavedDocument(
        user_id=user.id, title=req.title, category=req.category, content=req.content
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentListItem])
def list_documents(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SavedDocument]:
    return (
        db.query(SavedDocument)
        .filter(SavedDocument.user_id == user.id)
        .order_by(SavedDocument.created_at.desc())
        .all()
    )


@router.get("/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> SavedDocument:
    return _owned(db, user, doc_id)


@router.delete("/{doc_id}", status_code=204)
def delete_document(
    doc_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    doc = _owned(db, user, doc_id)
    db.delete(doc)
    db.commit()
    return Response(status_code=204)


@router.get("/{doc_id}/export")
def export_document(
    doc_id: int,
    format: str = "pdf",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    doc = _owned(db, user, doc_id)
    return _file_response(doc.title, doc.content, format)


def _owned(db: Session, user: User, doc_id: int) -> SavedDocument:
    doc = (
        db.query(SavedDocument)
        .filter(SavedDocument.id == doc_id, SavedDocument.user_id == user.id)
        .first()
    )
    if doc is None:
        raise HTTPException(status_code=404, detail="Document inexistent")
    return doc


# Export „stateless" — fără salvare, direct dintr-un rezultat de skill/chat.
export_router = APIRouter(prefix="/export", tags=["documents"])


@export_router.post("")
def export_inline(
    req: ExportRequest,
    user: User = Depends(get_current_user),
) -> Response:
    return _file_response(req.title, req.content, req.format)
