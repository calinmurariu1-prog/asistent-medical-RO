"""Medication schemas (Module 9)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class MedicationBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    active_substance: str | None = None
    dose: str | None = None
    frequency: str | None = None
    interval: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool = True
    notes: str | None = None


class MedicationCreate(MedicationBase):
    pass


class MedicationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    active_substance: str | None = None
    dose: str | None = None
    frequency: str | None = None
    interval: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None
    notes: str | None = None


class MedicationOut(MedicationBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


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
