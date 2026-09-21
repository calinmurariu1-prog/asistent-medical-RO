"""Patient profile schemas."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import AllergySeverity, BloodType, Sex


class PatientBase(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    birth_date: date | None = None
    sex: Sex | None = None
    weight_kg: float | None = Field(default=None, ge=0, le=700)
    height_cm: float | None = Field(default=None, ge=0, le=300)
    blood_type: BloodType | None = None
    phone: str | None = None
    family_doctor_id: int | None = None


class PatientUpdate(PatientBase):
    first_name: str | None = Field(default=None, max_length=120)
    last_name: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    family_doctor_id: int | None = Field(default=None, ge=1)
    # CNP is write-only; never returned in responses.
    cnp: str | None = Field(default=None, max_length=13)


class PatientOut(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bmi: float | None = None


class AllergyIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    substance: str = Field(min_length=1, max_length=200)
    reaction: str | None = Field(default=None, max_length=10000)
    severity: AllergySeverity = AllergySeverity.UNKNOWN


class AllergyOut(AllergyIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class EmergencyContactIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=1, max_length=200)
    relationship_label: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=40)


class EmergencyContactOut(EmergencyContactIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
