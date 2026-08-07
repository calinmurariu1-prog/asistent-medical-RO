"""Transactional email sending (SMTP), with a dev-safe logging fallback.

When SMTP is not configured, emails are logged instead of sent so local/dev and
tests never touch the network. Swap in an async queue for production volume.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send a plain-text email. Returns True if actually sent via SMTP."""
    if not settings.SMTP_HOST:
        logger.info("[email:dev] To=%s | %s\n%s", to, subject, body)
        return False

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001  (never let email break the request)
        logger.error("[email] send failed to %s: %s", to, exc)
        return False


def send_verification_email(to: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    send_email(
        to,
        "Confirmă adresa de email — Asistent Medical AI",
        "Bun venit! Confirmă-ți adresa de email accesând linkul de mai jos:\n\n"
        f"{link}\n\nDacă nu ai creat acest cont, ignoră mesajul.",
    )


def send_password_reset_email(to: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    send_email(
        to,
        "Resetare parolă — Asistent Medical AI",
        "Ai cerut resetarea parolei. Accesează linkul de mai jos (valabil 2 ore):\n\n"
        f"{link}\n\nDacă nu ai cerut acest lucru, ignoră mesajul.",
    )
