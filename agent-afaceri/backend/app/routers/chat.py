"""Rută de chat contextual cu agentul de afaceri & juridic."""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas.chat import ChatRequest, ChatResponse
from app.services.ai.base import DISCLAIMER
from app.services.ai.factory import get_provider

router = APIRouter(prefix="/chat", tags=["chat"])

_SYSTEM = {
    "juridic": (
        "Ești un asistent juridic informativ pentru România, răspunzi în limba "
        "română, clar și structurat. NU oferi consultanță juridică definitivă și "
        "recomanzi consultarea unui avocat pentru cazuri concrete. Dacă datele "
        "sunt insuficiente, spune ce informații mai sunt necesare."
    ),
    "business": (
        "Ești un consultant de afaceri informativ pentru România, răspunzi în "
        "limba română, clar și practic. NU oferi consultanță fiscală/contabilă "
        "definitivă și recomanzi verificarea cu un contabil sau ANAF. Dacă datele "
        "sunt insuficiente, spune ce informații mai sunt necesare."
    ),
}


@router.post("", response_model=ChatResponse)
def chat(req: ChatRequest) -> ChatResponse:
    provider = get_provider()
    system = _SYSTEM.get(req.domain, _SYSTEM["business"])

    history_txt = "\n".join(f"{m.role}: {m.content}" for m in req.history[-8:])
    user = (f"Conversație anterioară:\n{history_txt}\n\n" if history_txt else "") + (
        f"Întrebare: {req.message}"
    )

    if getattr(provider, "name", "") == "mock":
        reply = (
            "[mod demonstrativ — setează ANTHROPIC_API_KEY pentru răspunsuri reale]\n"
            f"Ai întrebat despre ({req.domain}): {req.message}\n\n{DISCLAIMER}"
        )
    else:
        text = provider.complete(system=system, user=user)
        reply = text if "orientativ" in text.lower() else f"{text}\n\n{DISCLAIMER}"

    return ChatResponse(reply=reply)
