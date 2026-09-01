"""Provider Anthropic Claude."""
from __future__ import annotations

from app.services.ai.base import AIProvider


class AnthropicProvider(AIProvider):
    """Provider bazat pe API-ul Anthropic (Claude)."""

    name = "anthropic"

    def __init__(self, api_key: str, model: str = "claude-sonnet-5") -> None:
        # Importat lazy ca serviciul să pornească și fără pachetul instalat.
        from anthropic import Anthropic

        self._client = Anthropic(api_key=api_key)
        self._model = model

    def complete(self, *, system: str, user: str) -> str:
        msg = self._client.messages.create(
            model=self._model,
            max_tokens=1500,
            temperature=0.3,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [block.text for block in msg.content if getattr(block, "type", "") == "text"]
        return "\n".join(parts).strip()
