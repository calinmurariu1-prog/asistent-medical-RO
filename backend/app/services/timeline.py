"""Module 6 - unified medical timeline across record types."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.clinical import MedicalHistory
from app.models.document import Document
from app.models.medication import Medication


@dataclass
class TimelineItem:
    date: date | None
    kind: str          # history | document | appointment | medication
    subtype: str | None
    title: str
    ref_id: int


def build_timeline(
    db: Session,
    patient_id: int,
    *,
    year: int | None = None,
    kinds: set[str] | None = None,
) -> list[TimelineItem]:
    items: list[TimelineItem] = []

    if kinds is None or "history" in kinds:
        for h in db.scalars(
            select(MedicalHistory).where(MedicalHistory.patient_id == patient_id)
        ):
            items.append(
                TimelineItem(h.event_date, "history", h.event_type.value, h.title, h.id)
            )

    if kinds is None or "document" in kinds:
        for d in db.scalars(
            select(Document).where(Document.patient_id == patient_id)
        ):
            items.append(
                TimelineItem(
                    d.document_date or d.created_at.date(),
                    "document",
                    d.category.value,
                    d.original_filename,
                    d.id,
                )
            )

    if kinds is None or "appointment" in kinds:
        for a in db.scalars(
            select(Appointment).where(Appointment.patient_id == patient_id)
        ):
            items.append(
                TimelineItem(a.starts_at.date(), "appointment", a.type.value, a.title, a.id)
            )

    if kinds is None or "medication" in kinds:
        for m in db.scalars(
            select(Medication).where(Medication.patient_id == patient_id)
        ):
            if m.start_date is not None:
                items.append(
                    TimelineItem(m.start_date, "medication", None, m.name, m.id)
                )

    if year is not None:
        items = [i for i in items if i.date and i.date.year == year]

    # Newest first; undated entries sink to the bottom.
    items.sort(key=lambda i: i.date or date.min, reverse=True)
    return items
