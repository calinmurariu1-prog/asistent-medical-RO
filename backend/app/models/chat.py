"""AI chat sessions and messages (Module 11)."""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, TimestampMixin
from app.models.enums import ChatRole

if TYPE_CHECKING:
    from app.models.patient import Patient


class AIChat(Base, TimestampMixin):
    __tablename__ = "ai_chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    patient_id: Mapped[int] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), index=True, nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(300), nullable=True)

    patient: Mapped[Patient] = relationship(back_populates="chats")
    messages: Mapped[list[AIChatMessage]] = relationship(
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="AIChatMessage.id",
    )


class AIChatMessage(Base, TimestampMixin):
    __tablename__ = "ai_chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("ai_chats.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[ChatRole] = mapped_column(Enum(ChatRole, native_enum=False), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # JSON list of source references (documents / lab results) used for RAG.
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)

    chat: Mapped[AIChat] = relationship(back_populates="messages")

    __table_args__ = (
        Index("ix_chat_messages_chat", "chat_id", "id"),
    )
