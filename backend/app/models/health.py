"""Imported health metrics (Apple Health / Google Health / Huawei Health)."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import HealthMetricType, HealthSource

if TYPE_CHECKING:
    from app.models.patient import Patient


class HealthSample(Base, TimestampMixin):
    """A single normalized measurement from a connected health platform.

    All vendor-specific identifiers and units are normalized upstream (see
    `app.services.health`) into a `HealthMetricType` + canonical unit before a
    row is created here.
    """

    __tablename__ = "health_samples"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source: Mapped[HealthSource] = mapped_column(
        Enum(HealthSource, native_enum=False, length=20), nullable=False
    )
    metric_type: Mapped[HealthMetricType] = mapped_column(
        Enum(HealthMetricType, native_enum=False, length=30), nullable=False
    )
    value: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    patient: Mapped[Patient] = relationship(back_populates="health_samples")

    __table_args__ = (
        # Idempotent imports: the same measurement can't land twice.
        UniqueConstraint(
            "patient_id",
            "source",
            "metric_type",
            "recorded_at",
            name="uq_health_sample_natural_key",
        ),
        Index("ix_health_samples_patient_metric", "patient_id", "metric_type"),
    )
