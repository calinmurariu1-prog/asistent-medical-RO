"""Module 2 - Patient profile endpoints."""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.core.security import encrypt_field
from app.models.clinical import Doctor
from app.models.patient import Allergy, Patient
from app.schemas.patient import (
    AllergyIn,
    AllergyOut,
    PatientOut,
    PatientUpdate,
)
from app.services import audit

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
    changed_fields = sorted(data)
    doctor_id = data.get("family_doctor_id")
    if doctor_id is not None and db.get(Doctor, doctor_id) is None:
        raise HTTPException(404, "Medicul selectat nu există.")
    if "cnp" in data:
        cnp = data.pop("cnp")
        patient.cnp_encrypted = encrypt_field(cnp) if cnp else None
    for key, value in data.items():
        setattr(patient, key, value)
    db.add(patient)
    # Field names only: profile content and the identifier never enter audit detail.
    audit.record(db, user_id=patient.user_id, action="patient_update",
                 resource_type="patient", resource_id=patient.id,
                 detail=json.dumps({"fields": changed_fields}))
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
    audit.record(db, user_id=patient.user_id, action="allergy_create",
                 resource_type="allergy", resource_id=allergy.id)
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
    audit.record(db, user_id=patient.user_id, action="allergy_delete",
                 resource_type="allergy", resource_id=allergy_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/me/allergies/{allergy_id}", response_model=AllergyOut)
def update_allergy(allergy_id: int, payload: AllergyIn,
                   patient: Patient = Depends(get_current_patient), db: Session = Depends(get_db)):
    allergy = db.get(Allergy, allergy_id)
    if allergy is None or allergy.patient_id != patient.id:
        raise HTTPException(404, "Alergie inexistentă")
    for key, value in payload.model_dump().items():
        setattr(allergy, key, value)
    db.commit()
    db.refresh(allergy)
    audit.record(db, user_id=patient.user_id, action="allergy_update",
                 resource_type="allergy", resource_id=allergy.id)
    return allergy
