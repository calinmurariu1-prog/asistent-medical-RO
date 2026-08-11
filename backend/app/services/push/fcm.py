"""Firebase Cloud Messaging (HTTP v1) push sender.

Sends to both Android and iOS (APNs via FCM). Authenticates with a service
account (JWT-bearer grant → OAuth token). Requires FCM_PROJECT_ID and
FCM_SERVICE_ACCOUNT_JSON; otherwise construction raises and the factory falls
back to the mock sender.
"""
from __future__ import annotations

import json
import logging
import time

import httpx

from app.core.config import settings
from app.services.push.base import PushMessage

logger = logging.getLogger(__name__)

_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


class FCMPushProvider:
    name = "fcm"

    def __init__(self) -> None:
        if not settings.FCM_PROJECT_ID or not settings.FCM_SERVICE_ACCOUNT_JSON:
            raise RuntimeError("FCM not configured")
        try:
            self._sa = json.loads(settings.FCM_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError as exc:
            raise RuntimeError("FCM_SERVICE_ACCOUNT_JSON invalid") from exc
        self._project = settings.FCM_PROJECT_ID

    def _access_token(self) -> str:
        import jwt  # pyjwt

        now = int(time.time())
        token_uri = self._sa.get("token_uri", "https://oauth2.googleapis.com/token")
        assertion = jwt.encode(
            {
                "iss": self._sa["client_email"],
                "scope": _SCOPE,
                "aud": token_uri,
                "iat": now,
                "exp": now + 3600,
            },
            self._sa["private_key"],
            algorithm="RS256",
        )
        resp = httpx.post(
            token_uri,
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
                "assertion": assertion,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def send(self, token: str, message: PushMessage) -> bool:
        try:
            access = self._access_token()
            resp = httpx.post(
                f"https://fcm.googleapis.com/v1/projects/{self._project}/messages:send",
                headers={"Authorization": f"Bearer {access}"},
                json={
                    "message": {
                        "token": token,
                        "notification": {
                            "title": message.title,
                            "body": message.body,
                        },
                        "data": {k: str(v) for k, v in message.data.items()},
                    }
                },
                timeout=15.0,
            )
            resp.raise_for_status()
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("[fcm] send failed: %s", exc)
            return False
