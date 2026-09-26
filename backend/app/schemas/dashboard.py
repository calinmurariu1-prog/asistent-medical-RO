"""Dashboard schemas (Module 12)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class LabSummaryBrief(BaseModel):
    total_analytes: int
    abnormal_count: int
    critical_count: int
    unknown_count: int


class RecentDocument(BaseModel):
    id: int
    original_filename: str
    category: str
    status: str
    created_at: datetime


class ActiveMedication(BaseModel):
    id: int
    name: str
    dose: str | None


class UpcomingAppointment(BaseModel):
    id: int
    title: str
    starts_at: datetime


class DashboardOut(BaseModel):
    lab_summary: LabSummaryBrief
    recent_documents: list[RecentDocument]
    active_medications: list[ActiveMedication]
    upcoming_appointments: list[UpcomingAppointment]
    alerts: list[str]
    recommendations_preview: list[str]
    unread_notifications: int
