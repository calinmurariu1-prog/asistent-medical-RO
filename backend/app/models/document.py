"""Uploaded documents and extracted lab results."""
from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import DocumentCategory, LabFlag, ProcessingStatus

if TYPE_CHECKING:
    from app.models.patient import Patient


class Document(Base, TimestampMixin):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    category: Mapped[DocumentCategory] = mapped_column(
        Enum(DocumentCategory, native_enum=False),
        default=DocumentCategory.OTHER,
        nullable=False,
    )
    original_filename: Mapped[str] = mapped_column(String(500), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(150), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Object-storage key in the S3/MinIO bucket.
    storage_key: Mapped[str] = mapped_column(String(700), nullable=False)

    document_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # AI / OCR extraction
    status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus, native_enum=False),
        default=ProcessingStatus.PENDING,
        nullable=False,
    )
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_metadata: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON blob
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="documents")
    lab_results: Mapped[list[LabResult]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_documents_patient_category", "patient_id", "category"),
    )


class LabResult(Base, TimestampMixin):
    """A single analyte value extracted from a lab document (or entered manually)."""
    __tablename__ = "lab_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"), index=True, nullable=True
    )

    analyte: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    loinc_code: Mapped[str | None] = mapped_column(String(20), nullable=True)
    value: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_text: Mapped[str | None] = mapped_column(String(200), nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ref_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ref_high: Mapped[float | None] = mapped_column(Float, nullable=True)
    flag: Mapped[LabFlag] = mapped_column(
        Enum(LabFlag, native_enum=False), default=LabFlag.NORMAL, nullable=False
    )
    measured_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="lab_results")
    document: Mapped[Document | None] = relationship(back_populates="lab_results")

    __table_args__ = (
        Index("ix_lab_patient_analyte_date", "patient_id", "analyte", "measured_on"),
    )
