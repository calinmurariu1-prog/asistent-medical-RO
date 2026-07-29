"""Select the AI provider from settings, degrading to the offline mock."""
from __future__ import annotations

import logging

from app.core.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.mock import MockProvider

logger = logging.getLogger(__name__)

_KEY_BY_PROVIDER = {
    "anthropic": lambda: settings.ANTHROPIC_API_KEY,
    "openai": lambda: settings.OPENAI_API_KEY,
    "gemini": lambda: settings.GEMINI_API_KEY,
}


def get_ai_provider() -> AIProvider:
    """FastAPI dependency. Returns a real provider if its key is set, else mock."""
    provider = settings.AI_DEFAULT_PROVIDER.lower()
    key_getter = _KEY_BY_PROVIDER.get(provider)

    if not key_getter or not key_getter():
        if provider != "mock":
            logger.info("AI provider '%s' has no API key; using offline mock.", provider)
        return MockProvider()

    from app.services.ai.llm import (
        AnthropicProvider,
        GeminiProvider,
        OpenAIProvider,
    )

    try:
        if provider == "anthropic":
            return AnthropicProvider()
        if provider == "openai":
            return OpenAIProvider()
        if provider == "gemini":
            return GeminiProvider()
    except Exception as exc:  # noqa: BLE001  (missing SDK, bad config)
        logger.warning("Failed to init provider '%s': %s; using mock.", provider, exc)

    return MockProvider()
