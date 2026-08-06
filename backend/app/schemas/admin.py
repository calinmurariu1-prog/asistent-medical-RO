"""Admin & feedback schemas (Module 15)."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import UserRole


class FeedbackCreate(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    rating: int | None = Field(default=None, ge=1, le=5)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    message: str
    rating: int | None
    created_at: datetime


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_email_verified: bool
    created_at: datetime


class AdminUserUpdate(BaseModel):
    role: UserRole | None = None
    is_active: bool | None = None


class AdminStats(BaseModel):
    users: int
    patients: int
    documents: int
    lab_results: int
    chats: int
    feedback: int


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    action: str
    resource_type: str | None
    resource_id: str | None
    ip_address: str | None
    created_at: datetime
