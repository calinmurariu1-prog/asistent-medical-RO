"""Module 6 - Unified medical timeline."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.patient import Patient
from app.schemas.timeline import TimelineItemOut
from app.services import timeline

router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.get("", response_model=list[TimelineItemOut])
def get_timeline(
    year: int | None = None,
    kinds: list[str] | None = Query(default=None),
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[TimelineItemOut]:
    items = timeline.build_timeline(
        db, patient.id, year=year, kinds=set(kinds) if kinds else None
    )
    return [TimelineItemOut(**i.__dict__) for i in items]
