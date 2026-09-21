"""Module 9 - Medications and interaction/duplicate checks."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
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
from app.services import audit, medication_check

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
    db.flush()
    audit.record(db, user_id=patient.user_id, action="medication.create",
                 resource_type="medication", resource_id=med.id)
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
        unassessed_pairs=result.unassessed_pairs,
        unidentified_medications=result.unidentified_medications,
    )


@router.patch("/{med_id}", response_model=MedicationOut)
def update_medication(
    med_id: int,
    payload: MedicationUpdate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Medication:
    locked = db.execute(update(Medication).where(
        Medication.id == med_id, Medication.patient_id == patient.id,
    ).values(is_active=Medication.is_active).execution_options(synchronize_session=False))
    if locked.rowcount != 1:
        raise HTTPException(404, "Medicament inexistent")
    med = db.get(Medication, med_id, populate_existing=True)
    changes = payload.model_dump(exclude_unset=True)
    if any(key in changes and changes[key] is None for key in ("name", "is_active")):
        raise HTTPException(422, "Numele și starea tratamentului sunt obligatorii")
    start = changes.get("start_date", med.start_date)
    end = changes.get("end_date", med.end_date)
    if start and end and end < start:
        raise HTTPException(422, "Data de sfârșit nu poate preceda data de început")
    for key, value in changes.items():
        setattr(med, key, value)
    audit.record(db, user_id=patient.user_id, action="medication.update",
                 resource_type="medication", resource_id=med.id)
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
    audit.record(db, user_id=patient.user_id, action="medication.delete",
                 resource_type="medication", resource_id=med_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
