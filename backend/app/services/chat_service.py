"""Module 11 - AI chat orchestration (RAG over the patient's record)."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import AIChat, AIChatMessage
from app.models.enums import ChatRole
from app.services.ai.base import AIProvider
from app.services.rag import build_context

# How many prior turns to include for conversational continuity.
HISTORY_TURNS = 6


def create_chat(db: Session, patient_id: int, title: str | None) -> AIChat:
    chat = AIChat(patient_id=patient_id, title=title)
    db.add(chat)
    db.commit()
    db.refresh(chat)
    return chat


def list_chats(db: Session, patient_id: int) -> list[AIChat]:
    stmt = (
        select(AIChat)
        .where(AIChat.patient_id == patient_id)
        .order_by(AIChat.created_at.desc())
    )
    return list(db.scalars(stmt).all())


def get_chat(db: Session, patient_id: int, chat_id: int) -> AIChat | None:
    chat = db.get(AIChat, chat_id)
    if chat is None or chat.patient_id != patient_id:
        return None
    return chat


def answer(db: Session, ai: AIProvider, chat: AIChat, question: str) -> AIChatMessage:
    """Persist the user question, run RAG + AI, persist and return the reply."""
    history = [(m.role.value, m.content) for m in chat.messages[-HISTORY_TURNS:]]

    user_msg = AIChatMessage(chat_id=chat.id, role=ChatRole.USER, content=question)
    db.add(user_msg)
    db.commit()

    retrieved = build_context(db, chat.patient_id, question)
    reply_text = ai.chat(
        question=question,
        context=retrieved.context_text,
        history=history,
    )

    assistant_msg = AIChatMessage(
        chat_id=chat.id,
        role=ChatRole.ASSISTANT,
        content=reply_text,
        sources=json.dumps(retrieved.sources, ensure_ascii=False),
    )
    db.add(assistant_msg)

    # Set a title from the first question if none was provided.
    if not chat.title:
        chat.title = question[:80]
        db.add(chat)

    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg
