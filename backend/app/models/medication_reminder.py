"""Explicit daily reminder schedules; never inferred from prescription text."""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class MedicationReminder(Base, TimestampMixin):
    __tablename__ = "medication_reminders"

    id: Mapped[int] = mapped_column(primary_key=True)
    medication_id: Mapped[int] = mapped_column(
        ForeignKey("medications.id", ondelete="CASCADE"), nullable=False, index=True)
    local_time: Mapped[str] = mapped_column(String(5), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    next_occurrence: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)

    __table_args__ = (UniqueConstraint("medication_id", "local_time", "timezone",
                                      name="uq_medication_reminder_time"),)
