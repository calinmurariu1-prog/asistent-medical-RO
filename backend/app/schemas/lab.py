"""Lab-result schemas (Module 5)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    model_config = ConfigDict(allow_inf_nan=False, str_strip_whitespace=True)

    analyte: str = Field(min_length=1, max_length=200)
    value: float | None = None
    value_text: str | None = Field(default=None, max_length=200)
    unit: str | None = Field(default=None, max_length=50)
    ref_low: float | None = None
    ref_high: float | None = None
    measured_on: date | None = None

    @model_validator(mode="after")
    def validate_result(self):
        if self.value is None and not self.value_text:
            raise ValueError("Introdu o valoare numerică sau un rezultat textual.")
        if self.ref_low is not None and self.ref_high is not None and self.ref_low > self.ref_high:
            raise ValueError("Limita inferioară nu poate depăși limita superioară.")
        return self


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
    comparison_warning: str | None = None


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
    unknown_count: int
    items: list[LabSummaryItem]
