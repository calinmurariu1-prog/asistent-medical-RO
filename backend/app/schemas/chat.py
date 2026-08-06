"""Chat schemas (Module 11)."""
from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ChatRole


class ChatCreate(BaseModel):
    title: str | None = Field(default=None, max_length=300)


class MessageIn(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: ChatRole
    content: str
    sources: list[dict] = []
    created_at: datetime

    @field_validator("sources", mode="before")
    @classmethod
    def _parse_sources(cls, v: object) -> list[dict]:
        if v is None or v == "":
            return []
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return []
        return v  # already a list


class ChatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str | None
    created_at: datetime


class ChatDetailOut(ChatOut):
    messages: list[MessageOut] = []
