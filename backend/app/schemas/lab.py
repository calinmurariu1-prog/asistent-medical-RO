"""Lab-result schemas (Module 5)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import LabFlag


class LabResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int | None = None
    analyte: str
    value: float | None
    value_text: str | None
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    flag: LabFlag
    measured_on: date | None
    ai_explanation: str | None = None
    confidence: str = "verified"


class ManualLabIn(BaseModel):
    analyte: str = Field(min_length=1, max_length=200)
    value: float | None = None
    value_text: str | None = None
    unit: str | None = None
    ref_low: float | None = None
    ref_high: float | None = None
    measured_on: date | None = None


class LabSeriesPoint(BaseModel):
    measured_on: date | None
    value: float | None
    unit: str | None
    flag: LabFlag


class LabSeries(BaseModel):
    analyte: str
    unit: str | None
    ref_low: float | None
    ref_high: float | None
    trend: str | None
    points: list[LabSeriesPoint]


class LabSummaryItem(BaseModel):
    analyte: str
    latest_value: float | None
    unit: str | None
    flag: LabFlag
    measured_on: date | None
    measurements: int
    trend: str | None


class LabSummary(BaseModel):
    total_analytes: int
    abnormal_count: int
    critical_count: int
    items: list[LabSummaryItem]
