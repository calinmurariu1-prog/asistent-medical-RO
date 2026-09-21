"""Orchestrates document extraction: OCR -> AI -> persistence (Module 4).

Runs synchronously within the request for now. In production this is the unit
of work to move onto a task queue (Celery/RQ) — the DB status field
(pending/processing/done/failed) already models that lifecycle.
"""
from __future__ import annotations

import json
import logging
import math
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.document import Document, LabResult
from app.models.enums import DocumentCategory, LabFlag, ProcessingStatus
from app.services import lab_analysis, ocr
from app.services.ai.base import AIProvider, ExtractedLabValue
from app.services.storage import Storage

logger = logging.getLogger(__name__)


def compute_flag(value: float | None, low: float | None, high: float | None) -> LabFlag:
    """Compare only with supplied bounds; never infer clinical critical thresholds."""
    if value is None or (low is None and high is None):
        return LabFlag.UNKNOWN
    if any(n is not None and not math.isfinite(n) for n in (value, low, high)):
        return LabFlag.UNKNOWN
    if low is not None and high is not None and low > high:
        return LabFlag.UNKNOWN
    if high is not None and value > high:
        return LabFlag.HIGH
    if low is not None and value < low:
        return LabFlag.LOW
    return LabFlag.NORMAL


def _persist_lab_values(
    db: Session, document: Document, values: list[ExtractedLabValue]
) -> None:
    for v in values:
        if not v.analyte:
            continue
        if any(n is not None and not math.isfinite(n) for n in (v.value, v.ref_low, v.ref_high)):
            raise ValueError("non_finite_lab_value")
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
    db.refresh(document)

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
        previous_analytes = list(db.scalars(select(LabResult.analyte).where(
            LabResult.document_id == document.id)))
        # Replace results only after extraction succeeds; rollback preserves prior rows.
        db.execute(delete(LabResult).where(LabResult.document_id == document.id))
        _persist_lab_values(db, document, extraction.lab_values)
        lab_analysis.invalidate_explanations(db, document.patient_id,
            previous_analytes + [v.analyte for v in extraction.lab_values])
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
