"""Wearables / health devices auto-detected from the platform data.

On mobile, every HealthKit / Health Connect sample carries the source device
(e.g. "Apple Watch Series 9"). The app reports those devices here so the user
sees what's connected — no file upload, no manual setup.
"""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import HealthSource

if TYPE_CHECKING:
    from app.models.patient import Patient


class HealthDevice(Base, TimestampMixin):
    __tablename__ = "health_devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[HealthSource] = mapped_column(
        Enum(HealthSource, native_enum=False), nullable=False
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    vendor: Mapped[str | None] = mapped_column(String(60), nullable=True)
    # JSON-encoded list of metric types this device provides.
    metrics: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    patient: Mapped[Patient] = relationship(back_populates="health_devices")

    __table_args__ = (
        UniqueConstraint(
            "patient_id", "source", "name", name="uq_health_device_natural_key"
        ),
    )
