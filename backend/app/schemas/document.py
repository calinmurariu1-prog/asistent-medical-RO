"""Document and lab-result schemas (Module 4)."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import DocumentCategory, LabFlag, ProcessingStatus


class LabResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analyte: str
    value: float | None
    value_text: str | None
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    flag: LabFlag
    measured_on: date | None
    ai_explanation: str | None = None


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
