"""Module 5 - Lab interpretation, comparison over time and charts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.document import LabResult
from app.models.enums import LabFlag
from app.models.patient import Patient
from app.schemas.lab import (
    LabResultOut,
    LabSeries,
    LabSeriesPoint,
    LabSummary,
    ManualLabIn,
)
from app.services import lab_analysis
from app.services.ai import get_ai_provider
from app.services.ai.base import AIProvider
from app.services.document_processing import compute_flag

router = APIRouter(prefix="/labs", tags=["labs"])


@router.get("", response_model=list[LabResultOut])
def list_results(
    analyte: str | None = None,
    flag: LabFlag | None = None,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[LabResult]:
    return lab_analysis.get_results(db, patient.id, analyte=analyte, flag=flag)


@router.get("/summary", response_model=LabSummary)
def summary(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> LabSummary:
    return LabSummary(**lab_analysis.build_summary(db, patient.id))


@router.get("/analytes", response_model=list[str])
def list_analytes(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[str]:
    stmt = (
        select(LabResult.analyte)
        .where(LabResult.patient_id == patient.id)
        .distinct()
        .order_by(LabResult.analyte)
    )
    return list(db.scalars(stmt).all())


@router.get("/series/{analyte}", response_model=LabSeries)
def analyte_series(
    analyte: str,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> LabSeries:
    series = lab_analysis.build_series(db, patient.id, analyte)
    if not series:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Nu există date pentru acest analit")
    latest = series[-1]
    return LabSeries(
        analyte=analyte,
        unit=latest.unit,
        ref_low=latest.ref_low if len({(r.ref_low, r.ref_high) for r in series}) == 1 else None,
        ref_high=latest.ref_high if len({(r.ref_low, r.ref_high) for r in series}) == 1 else None,
        comparison_warning=lab_analysis.comparison_warning(series),
        trend=lab_analysis.compute_trend(series),
        points=[
            LabSeriesPoint(
                measured_on=r.measured_on, value=r.value, unit=r.unit, flag=r.flag
            )
            for r in series
        ],
    )


@router.post("", response_model=LabResultOut, status_code=status.HTTP_201_CREATED)
def add_manual_result(
    payload: ManualLabIn,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> LabResult:
    result = LabResult(
        patient_id=patient.id,
        flag=compute_flag(payload.value, payload.ref_low, payload.ref_high),
        **payload.model_dump(),
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    return result


def _owned_result(result_id: int, patient: Patient, db: Session) -> LabResult:
    result = db.get(LabResult, result_id)
    if result is None or result.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rezultat inexistent")
    return result


@router.post("/{result_id}/explain", response_model=LabResultOut)
def explain_result(
    result_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai_provider),
) -> LabResult:
    result = _owned_result(result_id, patient, db)
    return lab_analysis.explain_result(db, ai, result)


@router.post("/explain-all", response_model=list[LabResultOut])
def explain_all(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai_provider),
) -> list[LabResult]:
    results = lab_analysis.get_results(db, patient.id)
    for result in results:
        if result.ai_explanation is None:
            lab_analysis.explain_result(db, ai, result)
    return lab_analysis.get_results(db, patient.id)
