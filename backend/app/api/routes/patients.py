"""Module 2 - Patient profile endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.core.security import encrypt_field
from app.models.patient import Allergy, Patient
from app.schemas.patient import (
    AllergyIn,
    AllergyOut,
    PatientOut,
    PatientUpdate,
)

router = APIRouter(prefix="/patients", tags=["patients"])


def _to_out(p: Patient) -> PatientOut:
    bmi = None
    if p.weight_kg and p.height_cm:
        h = p.height_cm / 100
        bmi = round(p.weight_kg / (h * h), 1)
    out = PatientOut.model_validate(p)
    out.bmi = bmi
    return out


@router.get("/me", response_model=PatientOut)
def get_my_profile(patient: Patient = Depends(get_current_patient)) -> PatientOut:
    return _to_out(patient)


@router.put("/me", response_model=PatientOut)
def update_my_profile(
    payload: PatientUpdate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> PatientOut:
    data = payload.model_dump(exclude_unset=True)
    cnp = data.pop("cnp", None)
    if cnp is not None:
        patient.cnp_encrypted = encrypt_field(cnp)
    for key, value in data.items():
        setattr(patient, key, value)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return _to_out(patient)


@router.get("/me/allergies", response_model=list[AllergyOut])
def list_allergies(
    patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)
) -> list[Allergy]:
    return list(
        db.scalars(select(Allergy).where(Allergy.patient_id == patient.id)).all()
    )


@router.post("/me/allergies", response_model=AllergyOut, status_code=status.HTTP_201_CREATED)
def add_allergy(
    payload: AllergyIn,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Allergy:
    allergy = Allergy(patient_id=patient.id, **payload.model_dump())
    db.add(allergy)
    db.commit()
    db.refresh(allergy)
    return allergy


@router.delete("/me/allergies/{allergy_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_allergy(
    allergy_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Response:
    allergy = db.get(Allergy, allergy_id)
    if allergy is None or allergy.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Allergy not found")
    db.delete(allergy)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
