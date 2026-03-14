"""Reusable SMTP email helpers for support and transactional mail."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from config import get_settings

logger = logging.getLogger(__name__)


def _is_configured() -> bool:
    settings = get_settings()
    return bool(
        settings.smtp_host
        and settings.smtp_user
        and settings.smtp_password
        and settings.smtp_from
    )


def send_email(*, to_email: str, subject: str, text_body: str, reply_to: str | None = None) -> bool:
    """Send an email via configured SMTP credentials."""
    settings = get_settings()
    if not _is_configured():
        logger.warning("SMTP is not configured; skipping email send: %s", subject)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_from}>"
    msg["To"] = to_email
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(text_body)

    try:
        if settings.smtp_secure:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=20) as server:
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)
        return True
    except Exception as exc:
        logger.error("Failed to send email to %s: %s", to_email, exc)
        return False


def send_support_request_email(*, name: str, email: str, message: str) -> bool:
    settings = get_settings()
    subject = f"Parently support request from {name}"
    body = (
        f"New support request from Parently web app.\n\n"
        f"Name: {name}\n"
        f"Email: {email}\n\n"
        f"Message:\n{message}\n"
    )
    return send_email(
        to_email=settings.support_email,
        subject=subject,
        text_body=body,
        reply_to=email,
    )
