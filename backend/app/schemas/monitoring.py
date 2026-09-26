"""Monitoring dashboard schemas (Module 8)."""
from __future__ import annotations

from pydantic import BaseModel


class MonitoringPoint(BaseModel):
    measured_on: str | None
    value: float | None
    flag: str


class MonitoringParam(BaseModel):
    analyte: str
    label: str
    group: str
    unit: str | None
    latest_value: float | None
    flag: str
    trend: str | None
    points: list[MonitoringPoint]
    comparison_warning: str | None = None


class MonitoringDashboardOut(BaseModel):
    chronic_conditions: list[str]
    groups: dict[str, list[MonitoringParam]]
    bmi: float | None = None
