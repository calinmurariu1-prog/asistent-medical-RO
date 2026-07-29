"""AI provider abstraction (Anthropic / OpenAI / Gemini) with offline fallback."""
from app.services.ai.base import (
    AIProvider,
    DocumentExtraction,
    ExtractedLabValue,
)
from app.services.ai.factory import get_ai_provider

__all__ = [
    "AIProvider",
    "DocumentExtraction",
    "ExtractedLabValue",
    "get_ai_provider",
]
