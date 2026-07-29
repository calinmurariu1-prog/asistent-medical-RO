"""Orchestrates document extraction: OCR -> AI -> persistence (Module 4).

Runs synchronously within the request for now. In production this is the unit
of work to move onto a task queue (Celery/RQ) — the DB status field
(pending/processing/done/failed) already models that lifecycle.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models.document import Document, LabResult
from app.models.enums import LabFlag, ProcessingStatus
from app.services import ocr
from app.services.ai.base import AIProvider, ExtractedLabValue
from app.services.storage import Storage

logger = logging.getLogger(__name__)


def compute_flag(value: float | None, low: float | None, high: float | None) -> LabFlag:
    """Classify a lab value against its reference interval."""
    if value is None or (low is None and high is None):
        return LabFlag.NORMAL
    if high is not None and value > high:
        span = (high - low) if (low is not None and high > low) else high
        if span and value > high + 0.5 * abs(span):
            return LabFlag.CRITICAL_HIGH
        return LabFlag.HIGH
    if low is not None and value < low:
        span = (high - low) if (high is not None and high > low) else low
        if span and value < low - 0.5 * abs(span):
            return LabFlag.CRITICAL_LOW
        return LabFlag.LOW
    return LabFlag.NORMAL


def _persist_lab_values(
    db: Session, document: Document, values: list[ExtractedLabValue]
) -> None:
    for v in values:
        if not v.analyte:
            continue
        db.add(
            LabResult(
                patient_id=document.patient_id,
                document_id=document.id,
                analyte=v.analyte,
                value=v.value,
                value_text=v.value_text,
                unit=v.unit,
                ref_low=v.ref_low,
                ref_high=v.ref_high,
                flag=compute_flag(v.value, v.ref_low, v.ref_high),
                measured_on=document.document_date,
            )
        )


def process_document(
    db: Session,
    document: Document,
    storage: Storage,
    ai: AIProvider,
) -> Document:
    """Download, extract text, run AI extraction and persist results."""
    document.status = ProcessingStatus.PROCESSING
    db.add(document)
    db.commit()

    try:
        data = storage.get(document.storage_key)
        text = ocr.extract_text(data, document.content_type, document.original_filename)
        extraction = ai.extract_document(text, document.category.value)

        document.extracted_text = text or None
        document.ai_summary = extraction.summary or None
        document.ai_metadata = json.dumps(extraction.to_metadata(), ensure_ascii=False)
        _persist_lab_values(db, document, extraction.lab_values)

        document.status = ProcessingStatus.DONE
        document.processed_at = datetime.now(UTC)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document %s processing failed", document.id)
        document.status = ProcessingStatus.FAILED
        document.ai_summary = f"Procesare eșuată: {exc}"

    db.add(document)
    db.commit()
    db.refresh(document)
    return document
