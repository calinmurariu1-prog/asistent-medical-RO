"""Durable cleanup intent survives account/document deletion and process restarts."""
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, TimestampMixin


class StorageDeletion(Base, TimestampMixin):
    __tablename__ = "storage_deletions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    backend: Mapped[str] = mapped_column(String(20), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    claimed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
