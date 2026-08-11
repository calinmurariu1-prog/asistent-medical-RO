"""Push-notification sender interface."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class PushMessage:
    title: str
    body: str = ""
    data: dict = field(default_factory=dict)


class PushProvider(Protocol):
    name: str

    def send(self, token: str, message: PushMessage) -> bool:
        """Deliver one message to a device token. Returns True on success."""
        ...
