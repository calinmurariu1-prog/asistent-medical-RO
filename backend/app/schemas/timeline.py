"""Timeline schemas (Module 6)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel


class TimelineItemOut(BaseModel):
    date: date | None
    kind: str
    subtype: str | None
    title: str
    ref_id: int
