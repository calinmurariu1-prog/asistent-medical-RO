"""Offline push sender for dev/tests — records sends, never hits the network."""
from __future__ import annotations

from app.services.push.base import PushMessage


class MockPushProvider:
    name = "mock"

    def __init__(self) -> None:
        self.sent: list[tuple[str, PushMessage]] = []

    def send(self, token: str, message: PushMessage) -> bool:
        # A token starting with "invalid" simulates a failed/expired token.
        if token.startswith("invalid"):
            return False
        self.sent.append((token, message))
        return True
