"""SMTP email delivery with a private local mailbox for development."""
from __future__ import annotations

import logging
import smtplib
import ssl
import uuid
from email.message import EmailMessage
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Return True when sent via SMTP or saved to the private development mailbox."""
    if not settings.SMTP_HOST:
        if settings.is_production:
            logger.warning("Email delivery is not configured")
            return False
        mailbox = Path(settings.LOCAL_DATA_DIR) / "mailbox"
        mailbox.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = mailbox / (uuid.uuid4().hex + ".txt")
        with path.open("x", encoding="utf-8") as output:
            output.write(f"To: {to}\nSubject: {subject}\n\n{body}")
        path.chmod(0o600)
        return True

    msg = EmailMessage()
    msg["From"] = settings.SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            if settings.SMTP_TLS:
                server.starttls(context=ssl.create_default_context())
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:  # noqa: BLE001  (never let email break the request)
        logger.error("Email delivery failed (%s)", type(exc).__name__)
        return False


def send_verification_email(to: str, token: str) -> bool:
    link = f"{settings.FRONTEND_URL}/verify-email#token={token}"
    return send_email(
        to,
        "Confirmă adresa de email — Asistent Medical AI",
        "Bun venit! Confirmă-ți adresa de email accesând linkul de mai jos:\n\n"
        f"{link}\n\nDacă nu ai creat acest cont, ignoră mesajul.",
    )


def send_password_reset_email(to: str, token: str) -> None:
    link = f"{settings.FRONTEND_URL}/reset-password#token={token}"
    send_email(
        to,
        "Resetare parolă — Asistent Medical AI",
        "Ai cerut resetarea parolei. Accesează linkul de mai jos (valabil 2 ore):\n\n"
        f"{link}\n\nDacă nu ai cerut acest lucru, ignoră mesajul.",
    )
