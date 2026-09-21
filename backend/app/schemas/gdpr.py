"""GDPR & consent schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

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
