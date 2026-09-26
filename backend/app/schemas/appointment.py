"""Appointment schemas (Module 10)."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    model_validator,
)

from app.models.enums import AppointmentStatus, AppointmentType

UTCDateTime = Annotated[AwareDatetime, AfterValidator(lambda value: value.astimezone(UTC))]


class AppointmentBase(BaseModel):
    type: AppointmentType = AppointmentType.CONSULTATION
    title: str = Field(min_length=1, max_length=300)
    location: str | None = None
    doctor_id: int | None = None
    starts_at: UTCDateTime
    ends_at: UTCDateTime | None = None
    notes: str | None = None


class AppointmentCreate(AppointmentBase):
    @model_validator(mode="after")
    def valid_interval(self):
        if self.ends_at and self.ends_at <= self.starts_at:
            raise ValueError("Sfârșitul trebuie să fie după începutul programării")
        return self


class AppointmentUpdate(BaseModel):
    type: AppointmentType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    location: str | None = None
    doctor_id: int | None = None
    starts_at: UTCDateTime | None = None
    ends_at: UTCDateTime | None = None
    status: AppointmentStatus | None = None
    notes: str | None = None


class AppointmentOut(AppointmentBase):
    model_config = ConfigDict(from_attributes=True)

    starts_at: datetime
    ends_at: datetime | None = None
    id: int
    status: AppointmentStatus

    @field_serializer("starts_at", "ends_at")
    def utc_dates(self, value):
        return value.replace(tzinfo=value.tzinfo or UTC).isoformat() if value else None
