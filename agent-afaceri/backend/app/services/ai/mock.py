"""Provider „mock" — deterministic, offline, fără cheie API.

Permite rularea aplicației și a testelor fără acces la un LLM real.
Răspunsurile efective vin din funcțiile `mock` ale fiecărui skill.
"""
from __future__ import annotations

from app.services.ai.base import AIProvider


class MockProvider(AIProvider):
    name = "mock"

    def complete(self, *, system: str, user: str) -> str:
        return (
            "[mod demonstrativ, fără AI real]\n"
            "Setează ANTHROPIC_API_KEY pentru răspunsuri generate de Claude.\n\n"
            + user[:400]
        )
