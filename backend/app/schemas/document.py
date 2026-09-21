"""Document schemas (Module 4)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentCategory, ProcessingStatus
from app.schemas.lab import LabResultOut

__all__ = [
    "LabResultOut",
    "DocumentOut",
    "DocumentDetailOut",
    "DocumentDownloadOut",
]


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: DocumentCategory
    original_filename: str
    content_type: str | None
    size_bytes: int | None
    document_date: date | None
    status: ProcessingStatus
    ai_summary: str | None
    processed_at: datetime | None
    created_at: datetime


class DocumentDetailOut(DocumentOut):
    extracted_text: str | None = None
    lab_results: list[LabResultOut] = []


class DocumentDownloadOut(BaseModel):
    url: str
    expires_in: int


class DocumentDateUpdate(BaseModel):
    document_date: date | None
