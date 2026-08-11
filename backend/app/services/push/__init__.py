"""Push notifications: device-token registry + FCM/mock sender.

The sender is chosen at runtime (FCM when configured, else a deterministic mock),
so reminders and alerts work end-to-end in dev/tests without credentials.
"""
from app.services.push import service
from app.services.push.base import PushMessage, PushProvider
from app.services.push.factory import get_push_provider

__all__ = ["PushMessage", "PushProvider", "get_push_provider", "service"]
