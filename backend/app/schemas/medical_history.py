"""Medical history & vaccine schemas (Module 3)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import MedicalEventType


class MedicalHistoryBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    event_type: MedicalEventType
    title: str = Field(min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    event_date: date | None = None
    is_chronic: bool = False
    diagnosis_id: int | None = None
    procedure_id: int | None = None
    doctor_id: int | None = None
    hospital_id: int | None = None


class MedicalHistoryCreate(MedicalHistoryBase):
    pass


class MedicalHistoryUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    event_type: MedicalEventType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = Field(default=None, max_length=10000)
    event_date: date | None = None
    is_chronic: bool | None = None
    diagnosis_id: int | None = None
    procedure_id: int | None = None
    doctor_id: int | None = None
    hospital_id: int | None = None


    @model_validator(mode="after")
    def non_null_required_fields(self):
        for key in ("event_type", "title", "is_chronic"):
            if key in self.model_fields_set and getattr(self, key) is None:
                raise ValueError("Tipul, titlul și starea cronică nu pot fi nule.")
        return self


class MedicalHistoryOut(MedicalHistoryBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class VaccineCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    dose: str | None = Field(default=None, max_length=100)
    administered_on: date | None = None
    provider: str | None = Field(default=None, max_length=200)


class VaccineOut(VaccineCreate):
    model_config = ConfigDict(from_attributes=True)
    id: int
