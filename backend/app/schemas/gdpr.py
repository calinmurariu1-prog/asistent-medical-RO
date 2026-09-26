"""GDPR & consent schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ConsentType


class DeleteAccountRequest(BaseModel):
    password: str
    confirm: bool = False


class ConsentIn(BaseModel):
    consent_type: ConsentType
    granted: bool
    provider: str | None = None


class ConsentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    consent_type: ConsentType
    granted: bool
    version: str
    created_at: datetime


class SensitiveExportRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    mfa_code: str | None = Field(default=None, max_length=64)
    include_cnp: bool = False
