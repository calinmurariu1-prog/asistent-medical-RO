"""Medical history & vaccine schemas (Module 3)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MedicalEventType


class MedicalHistoryBase(BaseModel):
    event_type: MedicalEventType
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    event_date: date | None = None
    is_chronic: bool = False
    diagnosis_id: int | None = None
    procedure_id: int | None = None
    doctor_id: int | None = None
    hospital_id: int | None = None


class MedicalHistoryCreate(MedicalHistoryBase):
    pass


class MedicalHistoryUpdate(BaseModel):
    event_type: MedicalEventType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    event_date: date | None = None
    is_chronic: bool | None = None
    diagnosis_id: int | None = None
    procedure_id: int | None = None
    doctor_id: int | None = None
    hospital_id: int | None = None


class MedicalHistoryOut(MedicalHistoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class VaccineCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    dose: str | None = None
    administered_on: date | None = None
    provider: str | None = None


class VaccineOut(VaccineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
