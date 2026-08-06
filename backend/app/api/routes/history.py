"""Module 3 - Medical history (dosar medical) & vaccines."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import extract, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.clinical import MedicalHistory
from app.models.enums import MedicalEventType
from app.models.patient import Patient, Vaccine
from app.schemas.medical_history import (
    MedicalHistoryCreate,
    MedicalHistoryOut,
    MedicalHistoryUpdate,
    VaccineCreate,
    VaccineOut,
)

router = APIRouter(prefix="/history", tags=["medical-history"])


@router.get("", response_model=list[MedicalHistoryOut])
def list_history(
    event_type: MedicalEventType | None = None,
    year: int | None = None,
    doctor_id: int | None = None,
    hospital_id: int | None = None,
    is_chronic: bool | None = None,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[MedicalHistory]:
    stmt = select(MedicalHistory).where(MedicalHistory.patient_id == patient.id)
    if event_type is not None:
        stmt = stmt.where(MedicalHistory.event_type == event_type)
    if year is not None:
        stmt = stmt.where(extract("year", MedicalHistory.event_date) == year)
    if doctor_id is not None:
        stmt = stmt.where(MedicalHistory.doctor_id == doctor_id)
    if hospital_id is not None:
        stmt = stmt.where(MedicalHistory.hospital_id == hospital_id)
    if is_chronic is not None:
        stmt = stmt.where(MedicalHistory.is_chronic.is_(is_chronic))
    stmt = stmt.order_by(MedicalHistory.event_date.desc().nullslast())
    return list(db.scalars(stmt).all())


@router.post("", response_model=MedicalHistoryOut, status_code=status.HTTP_201_CREATED)
def add_history(
    payload: MedicalHistoryCreate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> MedicalHistory:
    entry = MedicalHistory(patient_id=patient.id, **payload.model_dump())
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _owned(entry_id: int, patient: Patient, db: Session) -> MedicalHistory:
    entry = db.get(MedicalHistory, entry_id)
    if entry is None or entry.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Intrare inexistentă")
    return entry


@router.patch("/{entry_id}", response_model=MedicalHistoryOut)
def update_history(
    entry_id: int,
    payload: MedicalHistoryUpdate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> MedicalHistory:
    entry = _owned(entry_id, patient, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(entry, key, value)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(
    entry_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Response:
    db.delete(_owned(entry_id, patient, db))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# --- Vaccines (part of the medical record) ---------------------------------
@router.get("/vaccines", response_model=list[VaccineOut])
def list_vaccines(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[Vaccine]:
    return list(
        db.scalars(select(Vaccine).where(Vaccine.patient_id == patient.id)).all()
    )


@router.post("/vaccines", response_model=VaccineOut, status_code=status.HTTP_201_CREATED)
def add_vaccine(
    payload: VaccineCreate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Vaccine:
    vaccine = Vaccine(patient_id=patient.id, **payload.model_dump())
    db.add(vaccine)
    db.commit()
    db.refresh(vaccine)
    return vaccine


@router.delete("/vaccines/{vaccine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vaccine(
    vaccine_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Response:
    vaccine = db.get(Vaccine, vaccine_id)
    if vaccine is None or vaccine.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vaccin inexistent")
    db.delete(vaccine)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
