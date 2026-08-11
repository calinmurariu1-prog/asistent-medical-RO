"""Select the push provider, degrading to the mock sender."""
from __future__ import annotations

import logging

from app.core.config import settings
from app.services.push.base import PushProvider
from app.services.push.mock import MockPushProvider

logger = logging.getLogger(__name__)

# Cached so the MockPushProvider keeps its recorded sends within a process.
_mock = MockPushProvider()


def get_push_provider() -> PushProvider:
    try:
        from app.services.push.fcm import FCMPushProvider

        return FCMPushProvider()
    except Exception as exc:  # noqa: BLE001  (missing creds/SDK)
        if not settings.PUSH_ALLOW_MOCK:
            raise
        logger.info("FCM not configured (%s); using mock push sender.", exc)
        return _mock
