"""Module 11 - AI chat orchestration (RAG over the patient's record)."""
from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.chat import AIChat, AIChatMessage
from app.models.enums import ChatRole
from app.services.ai.base import DISCLAIMER, AIProvider
from app.services.ai.safety_router import EMERGENCY_SOURCES, emergency_reply
from app.services.rag import build_context

# How many prior turns to include for conversational continuity.
HISTORY_TURNS = 6

INSUFFICIENT_SOURCES = (
    "Nu am suficiente informații și surse relevante în dosarul tău medical pentru "
    "a răspunde verificabil la această întrebare. Încarcă documentele relevante "
    f"sau discută întrebarea cu medicul. {DISCLAIMER}"
)


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

    local_alert = emergency_reply(question)
    retrieved = None if local_alert else build_context(db, chat.patient_id, question)
    sources = EMERGENCY_SOURCES if local_alert else []
    reply_text = local_alert or INSUFFICIENT_SOURCES
    if retrieved is not None and not retrieved.is_empty:
        candidate = ai.chat(
            question=question,
            context=retrieved.context_text,
            history=history,
        )
        # This validates citation identity, not clinical correctness or entailment.
        cited = set(re.findall(r"\[(S[0-9]+)\]", candidate))
        available = {source["ref"] for source in retrieved.sources}
        if cited and cited <= available:
            reply_text = candidate
            if DISCLAIMER not in reply_text:
                reply_text = f"{reply_text} {DISCLAIMER}"
            sources = [source for source in retrieved.sources if source["ref"] in cited]

    assistant_msg = AIChatMessage(
        chat_id=chat.id,
        role=ChatRole.ASSISTANT,
        content=reply_text,
        sources=json.dumps(sources, ensure_ascii=False),
    )
    db.add(assistant_msg)

    # Set a title from the first question if none was provided.
    if not chat.title:
        chat.title = question[:80]
        db.add(chat)

    db.commit()
    db.refresh(assistant_msg)
    return assistant_msg
