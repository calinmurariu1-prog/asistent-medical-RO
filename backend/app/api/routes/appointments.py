"""Module 10 - Appointments / calendar."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.patient import Patient
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentUpdate,
)

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("", response_model=list[AppointmentOut])
def list_appointments(
    upcoming: bool = False,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[Appointment]:
    stmt = select(Appointment).where(Appointment.patient_id == patient.id)
    if upcoming:
        stmt = stmt.where(
            Appointment.starts_at >= datetime.now(UTC),
            Appointment.status == AppointmentStatus.SCHEDULED,
        )
    return list(db.scalars(stmt.order_by(Appointment.starts_at)).all())


@router.post("", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Appointment:
    appt = Appointment(patient_id=patient.id, **payload.model_dump())
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


def _owned(appt_id: int, patient: Patient, db: Session) -> Appointment:
    appt = db.get(Appointment, appt_id)
    if appt is None or appt.patient_id != patient.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Programare inexistentă")
    return appt


@router.get("/{appt_id}", response_model=AppointmentOut)
def get_appointment(
    appt_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Appointment:
    return _owned(appt_id, patient, db)


@router.patch("/{appt_id}", response_model=AppointmentOut)
def update_appointment(
    appt_id: int,
    payload: AppointmentUpdate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Appointment:
    appt = _owned(appt_id, patient, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(appt, key, value)
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


@router.delete("/{appt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appt_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Response:
    appt = _owned(appt_id, patient, db)
    db.delete(appt)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
