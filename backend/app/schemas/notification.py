"""Notification schemas (Module 14)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationChannel, NotificationStatus


class NotificationCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    body: str | None = None
    channel: NotificationChannel = NotificationChannel.PUSH
    scheduled_for: datetime | None = None


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    channel: NotificationChannel
    title: str
    body: str | None
    status: NotificationStatus
    scheduled_for: datetime | None
    sent_at: datetime | None
    resource_type: str | None
    resource_id: str | None
    created_at: datetime
