"""Module 10 - Appointments / calendar."""
from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient
from app.core.database import get_db
from app.models.appointment import Appointment
from app.models.enums import AppointmentStatus
from app.models.notification import Notification
from app.models.patient import Patient
from app.schemas.appointment import (
    AppointmentCreate,
    AppointmentOut,
    AppointmentUpdate,
)
from app.services.notification_service import sync_appointment_reminder

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
    db.flush()
    sync_appointment_reminder(db, user_id=patient.user_id, appointment=appt)
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
    locked = db.execute(update(Appointment).where(
        Appointment.id == appt_id, Appointment.patient_id == patient.id,
    ).values(status=Appointment.status).execution_options(synchronize_session=False))
    if locked.rowcount != 1:
        raise HTTPException(404, "Programare inexistentă")
    appt = db.get(Appointment, appt_id, populate_existing=True)
    changes = payload.model_dump(exclude_unset=True)
    for required in ("starts_at", "title", "status", "type"):
        if required in changes and changes[required] is None:
            raise HTTPException(422, "Câmp obligatoriu fără valoare")
    starts = changes.get("starts_at", appt.starts_at)
    ends = changes.get("ends_at", appt.ends_at)
    if ends and ends.replace(tzinfo=ends.tzinfo or UTC) <= starts.replace(
        tzinfo=starts.tzinfo or UTC
    ):
        raise HTTPException(422, "Sfârșitul trebuie să fie după începutul programării")
    for key, value in changes.items():
        setattr(appt, key, value)
    db.flush()
    if {"starts_at", "status", "title"}.intersection(changes):
        sync_appointment_reminder(db, user_id=patient.user_id, appointment=appt)
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
    db.flush()
    db.execute(delete(Notification).where(
        Notification.user_id == patient.user_id, Notification.resource_type == "appointment",
        Notification.resource_id == str(appt_id),
    ))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
