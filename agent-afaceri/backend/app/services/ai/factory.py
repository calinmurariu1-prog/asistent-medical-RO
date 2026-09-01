"""Alege providerul AI pe baza configurării.

Dacă providerul „anthropic" e cerut dar nu există cheie API (sau pachetul
nu e instalat), se face fallback automat la „mock", ca aplicația să
funcționeze mereu — util pentru dezvoltare locală și CI.
"""
from __future__ import annotations

from app.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.mock import MockProvider


def get_provider() -> AIProvider:
    if settings.ai_provider == "anthropic" and settings.anthropic_api_key:
        try:
            from app.services.ai.anthropic_provider import AnthropicProvider

            return AnthropicProvider(
                api_key=settings.anthropic_api_key,
                model=settings.anthropic_model,
            )
        except Exception:  # pachet lipsă / init eșuat -> demo offline
            return MockProvider()
    return MockProvider()
