"""Patient profile and directly-owned clinical sub-records."""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import AllergySeverity, BloodType, Sex

if TYPE_CHECKING:
    from app.models.appointment import Appointment
    from app.models.chat import AIChat
    from app.models.clinical import Doctor, MedicalHistory
    from app.models.document import Document, LabResult
    from app.models.health import HealthSample
    from app.models.medication import Medication
    from app.models.user import User


class Patient(Base, TimestampMixin):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False
    )

    first_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    last_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # CNP is sensitive: stored encrypted at rest (AES via security.encrypt_field).
    cnp_encrypted: Mapped[str | None] = mapped_column(String(255), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sex: Mapped[Sex | None] = mapped_column(Enum(Sex, native_enum=False), nullable=True)

    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    blood_type: Mapped[BloodType | None] = mapped_column(
        Enum(BloodType, native_enum=False), nullable=True
    )

    family_doctor_id: Mapped[int | None] = mapped_column(
        ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True
    )
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)

    user: Mapped[User] = relationship(back_populates="patient")
    family_doctor: Mapped[Doctor | None] = relationship()

    allergies: Mapped[list[Allergy]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    vaccines: Mapped[list[Vaccine]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    emergency_contacts: Mapped[list[EmergencyContact]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    medical_history: Mapped[list[MedicalHistory]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    lab_results: Mapped[list[LabResult]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    medications: Mapped[list[Medication]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    appointments: Mapped[list[Appointment]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    chats: Mapped[list[AIChat]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )
    health_samples: Mapped[list[HealthSample]] = relationship(
        back_populates="patient", cascade="all, delete-orphan"
    )


class Allergy(Base, TimestampMixin):
    __tablename__ = "allergies"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    substance: Mapped[str] = mapped_column(String(200), nullable=False)
    reaction: Mapped[str | None] = mapped_column(Text, nullable=True)
    severity: Mapped[AllergySeverity] = mapped_column(
        Enum(AllergySeverity, native_enum=False), default=AllergySeverity.UNKNOWN
    )

    patient: Mapped[Patient] = relationship(back_populates="allergies")


class Vaccine(Base, TimestampMixin):
    __tablename__ = "vaccines"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    dose: Mapped[str | None] = mapped_column(String(100), nullable=True)
    administered_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(200), nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="vaccines")


class EmergencyContact(Base, TimestampMixin):
    __tablename__ = "emergency_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    relationship_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="emergency_contacts")
