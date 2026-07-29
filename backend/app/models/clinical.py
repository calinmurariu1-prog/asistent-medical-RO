"""Clinical reference entities and the unified medical-history timeline."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import Date, Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import MedicalEventType

if TYPE_CHECKING:
    from app.models.patient import Patient


class Doctor(Base, TimestampMixin):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    specialty: Mapped[str | None] = mapped_column(String(150), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hospital_id: Mapped[int | None] = mapped_column(
        ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True
    )

    hospital: Mapped[Hospital | None] = relationship(back_populates="doctors")


class Hospital(Base, TimestampMixin):
    __tablename__ = "hospitals"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)

    doctors: Mapped[list[Doctor]] = relationship(back_populates="hospital")


class Diagnosis(Base, TimestampMixin):
    """Reference/coded diagnosis (ICD-10) linked from history entries."""
    __tablename__ = "diagnoses"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)  # ICD-10
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class Procedure(Base, TimestampMixin):
    """Reference/coded procedure linked from history entries."""
    __tablename__ = "procedures"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str | None] = mapped_column(String(20), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class MedicalHistory(Base, TimestampMixin):
    """A single dated entry in the patient's medical timeline.

    Covers diagnoses, procedures, surgeries, hospitalizations, treatments,
    chronic conditions and family history via `event_type`.
    """
    __tablename__ = "medical_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_type: Mapped[MedicalEventType] = mapped_column(
        Enum(MedicalEventType, native_enum=False), nullable=False
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_chronic: Mapped[bool] = mapped_column(default=False, nullable=False)

    diagnosis_id: Mapped[int | None] = mapped_column(
        ForeignKey("diagnoses.id", ondelete="SET NULL"), nullable=True
    )
    procedure_id: Mapped[int | None] = mapped_column(
        ForeignKey("procedures.id", ondelete="SET NULL"), nullable=True
    )
    doctor_id: Mapped[int | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True
    )
    hospital_id: Mapped[int | None] = mapped_column(
        ForeignKey("hospitals.id", ondelete="SET NULL"), nullable=True
    )

    patient: Mapped[Patient] = relationship(back_populates="medical_history")
    diagnosis: Mapped[Diagnosis | None] = relationship()
    procedure: Mapped[Procedure | None] = relationship()

    __table_args__ = (
        Index("ix_history_patient_type_date", "patient_id", "event_type", "event_date"),
    )
