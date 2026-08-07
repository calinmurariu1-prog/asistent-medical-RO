"""Schemas for the health-data import module."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import HealthMetricType, HealthSource


class ImportResultOut(BaseModel):
    source: HealthSource
    imported: int
    duplicates: int
    skipped: int
    metrics: dict[str, int]
    message: str


class HealthMetricSummary(BaseModel):
    metric_type: str
    label: str
    unit: str
    count: int
    min: float | None = None
    max: float | None = None
    avg: float | None = None
    latest_value: float | None = None
    latest_at: str | None = None


class HealthSummaryOut(BaseModel):
    total_samples: int
    connected_sources: list[str]
    metrics: list[HealthMetricSummary]


class HealthSampleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: HealthSource
    metric_type: HealthMetricType
    value: float
    unit: str
    recorded_at: datetime


class HealthSampleIn(BaseModel):
    type: str                      # canonical metric type or a known alias
    value: float
    unit: str | None = None
    recorded_at: datetime


class HealthImportJsonRequest(BaseModel):
    """Normalized samples pushed directly (e.g. from native HealthKit / Health
    Connect on the mobile app)."""

    samples: list[HealthSampleIn]


class HealthSourceInfo(BaseModel):
    source: HealthSource
    label: str
    connected: bool
    sample_count: int
    how_to: str
    accepts: str
