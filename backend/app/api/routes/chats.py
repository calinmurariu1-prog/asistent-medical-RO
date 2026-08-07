"""Module 11 - Medical AI chat endpoints (RAG over the patient's record)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_patient, require_ai_consent
from app.core.database import get_db
from app.models.chat import AIChat, AIChatMessage
from app.models.patient import Patient
from app.schemas.chat import (
    ChatCreate,
    ChatDetailOut,
    ChatOut,
    MessageIn,
    MessageOut,
)
from app.services import chat_service
from app.services.ai import get_ai_provider
from app.services.ai.base import AIProvider

router = APIRouter(prefix="/chats", tags=["chat"])


@router.post("", response_model=ChatOut, status_code=status.HTTP_201_CREATED)
def create_chat(
    payload: ChatCreate,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> AIChat:
    return chat_service.create_chat(db, patient.id, payload.title)


@router.get("", response_model=list[ChatOut])
def list_chats(
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> list[AIChat]:
    return chat_service.list_chats(db, patient.id)


def _owned_chat(chat_id: int, patient: Patient, db: Session) -> AIChat:
    chat = chat_service.get_chat(db, patient.id, chat_id)
    if chat is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversație inexistentă")
    return chat


@router.get("/{chat_id}", response_model=ChatDetailOut)
def get_chat(
    chat_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> AIChat:
    return _owned_chat(chat_id, patient, db)


@router.post(
    "/{chat_id}/messages",
    response_model=MessageOut,
    dependencies=[Depends(require_ai_consent)],
)
def post_message(
    chat_id: int,
    payload: MessageIn,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
    ai: AIProvider = Depends(get_ai_provider),
) -> AIChatMessage:
    chat = _owned_chat(chat_id, patient, db)
    return chat_service.answer(db, ai, chat, payload.content)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    chat_id: int,
    patient: Patient = Depends(get_current_patient),
    db: Session = Depends(get_db),
) -> Response:
    chat = _owned_chat(chat_id, patient, db)
    db.delete(chat)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
