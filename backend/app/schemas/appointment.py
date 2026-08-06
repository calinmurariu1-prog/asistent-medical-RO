"""Appointment schemas (Module 10)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AppointmentStatus, AppointmentType


class AppointmentBase(BaseModel):
    type: AppointmentType = AppointmentType.CONSULTATION
    title: str = Field(min_length=1, max_length=300)
    location: str | None = None
    doctor_id: int | None = None
    starts_at: datetime
    ends_at: datetime | None = None
    notes: str | None = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    type: AppointmentType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    location: str | None = None
    doctor_id: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    status: AppointmentStatus | None = None
    notes: str | None = None


class AppointmentOut(AppointmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: AppointmentStatus
