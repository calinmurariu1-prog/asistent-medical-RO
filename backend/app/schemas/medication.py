"""Medication schemas (Module 9)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MedicationBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=200)
    active_substance: str | None = Field(default=None, max_length=200)
    dose: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    interval: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool = True
    notes: str | None = Field(default=None, max_length=4000)


class MedicationCreate(MedicationBase):
    @model_validator(mode="after")
    def valid_period(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("Data de sfârșit nu poate preceda data de început")
        return self


class MedicationUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    active_substance: str | None = Field(default=None, max_length=200)
    dose: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    interval: str | None = Field(default=None, max_length=100)
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=4000)


class MedicationOut(BaseModel):
    # New input limits must not make legacy records unreadable.
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    active_substance: str | None
    dose: str | None
    frequency: str | None
    interval: str | None
    start_date: date | None
    end_date: date | None
    is_active: bool
    notes: str | None


class InteractionWarningOut(BaseModel):
    drug_a: str
    drug_b: str
    severity: str
    description: str


class DuplicateWarningOut(BaseModel):
    substance: str
    medications: list[str]


class MedicationCheckOut(BaseModel):
    interactions: list[InteractionWarningOut]
    duplicates: list[DuplicateWarningOut]
    disclaimer: str
