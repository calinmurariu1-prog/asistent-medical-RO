"""Orchestrates document extraction: OCR -> AI -> persistence (Module 4).

Runs synchronously within the request for now. In production this is the unit
of work to move onto a task queue (Celery/RQ) — the DB status field
(pending/processing/done/failed) already models that lifecycle.
"""
from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from app.models.document import Document, LabResult
from app.models.enums import DocumentCategory, LabFlag, ProcessingStatus
from app.services import ocr
from app.services.ai.base import AIProvider, ExtractedLabValue
from app.services.storage import Storage

logger = logging.getLogger(__name__)


def compute_flag(value: float | None, low: float | None, high: float | None) -> LabFlag:
    """Classify a lab value against its reference interval.

    "Critical" uses a generic multiplicative margin relative to the exceeded
    bound (>=50% above the upper limit, or <=50% below the lower limit), since
    a domain-agnostic parser cannot know analyte-specific panic values. Refine
    per-analyte thresholds later if a clinical table is added.
    """
    if value is None or (low is None and high is None):
        return LabFlag.NORMAL
    if high is not None and value > high:
        if high > 0 and value >= high * 1.5:
            return LabFlag.CRITICAL_HIGH
        return LabFlag.HIGH
    if low is not None and value < low:
        if low > 0 and value <= low * 0.5:
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
                confidence=getattr(v, "confidence", "verified"),
            )
        )


class DocumentBusyError(Exception):
    pass


def process_document(
    db: Session,
    document: Document,
    storage: Storage,
    ai: AIProvider,
) -> Document:
    """Download, extract text, run AI extraction and persist results."""
    claimed = db.execute(update(Document).where(
        Document.id == document.id, Document.status != ProcessingStatus.PROCESSING,
    ).values(status=ProcessingStatus.PROCESSING))
    if claimed.rowcount != 1:
        db.rollback()
        raise DocumentBusyError()
    db.commit()

    try:
        data = storage.get(document.storage_key)
        text = ocr.extract_text(data, document.content_type, document.original_filename)
        if not text.strip():
            raise ValueError("empty_extraction")
        if len(text) > 200_000:
            raise ValueError("extraction_too_large")
        extraction = ai.extract_document(text, document.category.value)

        document.extracted_text = text or None
        document.ai_summary = extraction.summary or None
        document.ai_metadata = json.dumps(extraction.to_metadata(), ensure_ascii=False)
        # Replace results only after extraction succeeds; rollback preserves prior rows.
        db.execute(delete(LabResult).where(LabResult.document_id == document.id))
        _persist_lab_values(db, document, extraction.lab_values)
        if document.category == DocumentCategory.OTHER and extraction.lab_values:
            document.category = DocumentCategory.LAB

        document.status = ProcessingStatus.DONE
        document.processed_at = datetime.now(UTC)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("Document %s processing failed (%s)", document.id, type(exc).__name__)
        document.status = ProcessingStatus.FAILED
        document.ai_summary = (
            "Textul nu a putut fi extras sau procesat. Originalul este păstrat. "
            "Pentru scanări, verifică disponibilitatea OCR. Rezultatele anterioare sunt păstrate."
        )

    db.add(document)
    db.commit()
    db.refresh(document)
    db.expire(document, ["lab_results"])
    return document
