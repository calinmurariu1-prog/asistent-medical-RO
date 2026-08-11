"""Device push tokens registered by the mobile apps (FCM / APNs)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class PushToken(Base, TimestampMixin):
    __tablename__ = "push_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    token: Mapped[str] = mapped_column(String(400), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)  # ios|android|web

    user: Mapped[User] = relationship()
