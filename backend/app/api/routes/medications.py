"""Module 9 - Medications and interaction/duplicate checks."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.medication import Medication
from app.models.patient import Patient
from app.schemas.medication import (
    MedicationCheckOut,
    MedicationCreate,
    MedicationOut,
    MedicationUpdate,
)
from app.services import medication_check

router = APIRouter(prefix="/medications", tags=["medications"])


@router.get("", response_model=list[MedicationOut])
def list_medications(
    active_only: bool = False,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[Medication]:
    stmt = select(Medication).where(Medication.patient_id == patient.id)
    if active_only:
        stmt = stmt.where(Medication.is_active.is_(True))
    return list(db.scalars(stmt.order_by(Medication.name)).all())


@router.post("", response_model=MedicationOut, status_code=status.HTTP_201_CREATED)
def add_medication(
    payload: MedicationCreate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Medication:
    med = Medication(patient_id=patient.id, **payload.model_dump())
    db.add(med)
    db.commit()
    db.refresh(med)
    return med


def _owned(med_id: int, patient: Patient, db: Session) -> Medication:
    med = db.get(Medication, med_id)
    if med is None or med.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medicament inexistent")
    return med


@router.get("/check", response_model=MedicationCheckOut)
def check_interactions(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> MedicationCheckOut:
    meds = list(
        db.scalars(
            select(Medication).where(Medication.patient_id == patient.id)
        ).all()
    )
    result = medication_check.check_medications(meds)
    return MedicationCheckOut(
        interactions=[w.__dict__ for w in result.interactions],
        duplicates=[w.__dict__ for w in result.duplicates],
        disclaimer=result.disclaimer,
    )


@router.patch("/{med_id}", response_model=MedicationOut)
def update_medication(
    med_id: int,
    payload: MedicationUpdate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Medication:
    med = _owned(med_id, patient, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(med, key, value)
    db.add(med)
    db.commit()
    db.refresh(med)
    return med


@router.delete("/{med_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_medication(
    med_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Response:
    med = _owned(med_id, patient, db)
    db.delete(med)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
