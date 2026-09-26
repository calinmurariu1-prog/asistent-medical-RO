"""Module 5 - Lab interpretation, comparison over time and charts."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient, require_ai_consent
from app.core.database import get_db
from app.models.document import Document, LabResult
from app.models.enums import LabFlag, ProcessingStatus
from app.models.patient import Patient
from app.schemas.lab import (
    LabResultOut,
    LabSeries,
    LabSeriesPoint,
    LabSummary,
    ManualLabIn,
)
from app.services import audit, lab_analysis
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
    lab_analysis.invalidate_explanations(db, patient.id, [payload.analyte])
    db.flush()
    audit.record(db, user_id=patient.user_id, action="lab.create",
                 resource_type="lab_result", resource_id=result.id)
    db.refresh(result)
    return result


def _owned_result(result_id: int, patient: Patient, db: Session) -> LabResult:
    result = db.get(LabResult, result_id)
    if result is None or result.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rezultat inexistent")
    return result


def _editable_result(result_id: int, patient: Patient, db: Session) -> LabResult:
    result = _owned_result(result_id, patient, db)
    if result.document_id is not None:
        # Serialize against processing claims; never correct a row being replaced.
        locked = db.execute(
            update(Document).where(
                Document.id == result.document_id,
                Document.patient_id == patient.id,
                Document.status != ProcessingStatus.PROCESSING,
            ).values(status=Document.status).execution_options(synchronize_session=False)
        )
        if locked.rowcount != 1:
            raise HTTPException(409, "Documentul se procesează. Reîncearcă după finalizare.")
        result = db.scalar(select(LabResult).where(
            LabResult.id == result_id, LabResult.patient_id == patient.id,
        ).execution_options(populate_existing=True))
        if result is None:
            raise HTTPException(404, "Rezultatul a fost înlocuit. Reîncarcă lista.")
    return result


@router.put("/{result_id}", response_model=LabResultOut)
def update_result(
    result_id: int,
    payload: ManualLabIn,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> LabResult:
    result = _editable_result(result_id, patient, db)
    previous_analyte = result.analyte
    for key, value in payload.model_dump().items():
        setattr(result, key, value)
    result.flag = compute_flag(payload.value, payload.ref_low, payload.ref_high)
    result.confidence = "verified"  # User transcription, not medical validation.
    result.loinc_code = None
    result.ai_explanation = None
    lab_analysis.invalidate_explanations(db, patient.id, [previous_analyte, payload.analyte])
    audit.record(db, user_id=patient.user_id, action="lab.update",
                 resource_type="lab_result", resource_id=result.id)
    db.refresh(result)
    return result


@router.delete("/{result_id}", status_code=204)
def delete_result(
    result_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> None:
    result = _editable_result(result_id, patient, db)
    analyte = result.analyte
    db.delete(result)
    lab_analysis.invalidate_explanations(db, patient.id, [analyte])
    audit.record(db, user_id=patient.user_id, action="lab.delete",
                 resource_type="lab_result", resource_id=result_id)


@router.post("/{result_id}/explain", response_model=LabResultOut,
             dependencies=[Depends(require_ai_consent)])
def explain_result(
    result_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai_provider),
) -> LabResult:
    result = _owned_result(result_id, patient, db)
    try:
        return lab_analysis.explain_result(db, ai, result)
    except lab_analysis.LabExplanationChanged as exc:
        raise HTTPException(
            409, "Rezultatul s-a modificat. Reîncarcă și repetă explicația."
        ) from exc


@router.post("/explain-all", response_model=list[LabResultOut],
             dependencies=[Depends(require_ai_consent)])
def explain_all(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai_provider),
) -> list[LabResult]:
    patient_id = patient.id
    ids = [result.id for result in lab_analysis.get_results(db, patient_id)]
    for result_id in ids:
        result = db.get(LabResult, result_id, populate_existing=True)
        if result is not None and result.patient_id == patient_id and result.ai_explanation is None:
            try:
                lab_analysis.explain_result(db, ai, result)
            except lab_analysis.LabExplanationChanged:
                continue  # Changed/deleted values will appear fresh, without stale text.
    db.expire_all()
    return lab_analysis.get_results(db, patient_id)
