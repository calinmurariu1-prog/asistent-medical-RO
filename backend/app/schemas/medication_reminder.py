"""Daily schedule inputs require an explicit wall-clock time and IANA zone."""
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class ReminderInput(BaseModel):
    local_time: str = Field(pattern=r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    timezone: str = Field(min_length=1, max_length=64)
    is_enabled: bool = True

    @field_validator("timezone")
    @classmethod
    def known_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Fus orar IANA necunoscut") from exc
        return value


class ReminderOut(ReminderInput):
    model_config = ConfigDict(from_attributes=True)
    id: int
    medication_id: int
    next_occurrence: datetime | None

    @field_serializer("next_occurrence")
    def utc_date(self, value):
        return value.replace(tzinfo=value.tzinfo or UTC).isoformat() if value else None
