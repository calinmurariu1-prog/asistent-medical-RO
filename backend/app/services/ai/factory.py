"""Select the AI provider from settings, degrading to the offline mock."""
from __future__ import annotations

import logging
import time

from app.core.config import settings
from app.services.ai.base import AIProvider
from app.services.ai.mock import MockProvider

logger = logging.getLogger(__name__)

# TTL-cached MedLLM health so we don't ping the micro-service on every request.
_health_cache: dict[str, float | bool] = {"ts": 0.0, "ok": False}


def reset_medllm_health_cache() -> None:
    _health_cache.update(ts=0.0, ok=False)


def _medllm_healthy(provider) -> bool:
    now = time.monotonic()
    if now - float(_health_cache["ts"]) < settings.MED_LLM_HEALTH_TTL:
        return bool(_health_cache["ok"])
    ok = provider.health_check()
    _health_cache.update(ts=now, ok=ok)
    return ok

_KEY_BY_PROVIDER = {
    "anthropic": lambda: settings.ANTHROPIC_API_KEY,
    "openai": lambda: settings.OPENAI_API_KEY,
    "gemini": lambda: settings.GEMINI_API_KEY,
    "groq": lambda: settings.GROQ_API_KEY,
}


def get_ai_provider() -> AIProvider:
    """FastAPI dependency. Returns a real provider if its key is set, else mock."""
    provider = settings.AI_DEFAULT_PROVIDER.lower()

    # MedLLM talks to a micro-service (no API key here); handle it first.
    if provider == "medllm":
        try:
            from app.services.ai.med_llm import MedLLMProvider

            med = MedLLMProvider()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to init MedLLM provider: %s; using mock.", type(exc).__name__)
            return MockProvider()
        if settings.MED_LLM_FALLBACK_MOCK and not _medllm_healthy(med):
            logger.info("MedLLM micro-service unreachable; using offline mock.")
            return MockProvider()
        return med

    key_getter = _KEY_BY_PROVIDER.get(provider)

    if not key_getter or not key_getter():
        if provider != "mock":
            logger.info("AI provider '%s' has no API key; using offline mock.", provider)
        return MockProvider()

    from app.services.ai.llm import (
        AnthropicProvider,
        GeminiProvider,
        GroqProvider,
        OpenAIProvider,
    )

    try:
        if provider == "anthropic":
            return AnthropicProvider()
        if provider == "openai":
            return OpenAIProvider()
        if provider == "gemini":
            return GeminiProvider()
        if provider == "groq":
            return GroqProvider()
    except Exception as exc:  # noqa: BLE001  (missing SDK, bad config)
        logger.warning("Failed to init provider '%s': %s; using mock.", provider,
                       type(exc).__name__)

    return MockProvider()
