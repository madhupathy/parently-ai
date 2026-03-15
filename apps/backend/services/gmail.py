"""Gmail helper utilities for Parently.

Supports:
  - Legacy broad fetch (fetch_messages)
  - Targeted per-child fetch with search profiles (fetch_messages_targeted)
  - Incremental sync via GmailMessageIndex dedup
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import get_settings
from services.integration_state import GMAIL_SCOPE, extract_oauth_payload, gmail_connector_ready
from storage import get_db
from storage.models import UserIntegration

logger = logging.getLogger(__name__)

SCOPES = [GMAIL_SCOPE]


def _load_credentials_from_file(token_path: Path, client_secrets_path: Path) -> Credentials:
    if not token_path.exists():
        raise FileNotFoundError(f"Gmail token not found at {token_path}")

    with token_path.open("r", encoding="utf-8") as fh:
        token_data = json.load(fh)

    credentials = Credentials.from_authorized_user_info(token_data, scopes=SCOPES)
    if not credentials.valid and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    logger.info("Gmail auth source=file token_path=%s", token_path)
    return credentials


def _credentials_from_db_token(user_id: int) -> Optional[Credentials]:
    settings = get_settings()
    db = get_db()
    with db.session_scope() as session:
        integration = (
            session.query(UserIntegration)
            .filter(
                UserIntegration.user_id == user_id,
                UserIntegration.provider == "gmail",
                UserIntegration.status.in_(("connected", "scope_missing")),
            )
            .first()
        )
        if not integration:
            logger.info("Gmail auth unavailable: no gmail integration row for user_id=%s", user_id)
            return None

        token_payload = extract_oauth_payload(integration)
        has_scope = GMAIL_SCOPE in (integration.granted_scopes or "")
        has_oauth = gmail_connector_ready(integration)
        logger.info(
            "Gmail auth check: user_id=%s integration_status=%s has_scope=%s oauth_ready=%s has_access_token=%s has_refresh_token=%s",
            user_id,
            integration.status,
            has_scope,
            has_oauth,
            bool(token_payload.get("access_token")),
            bool(token_payload.get("refresh_token")),
        )
        if not has_scope or not has_oauth:
            logger.warning(
                "Gmail auth incomplete for user_id=%s (missing OAuth fields/scope); skipping Gmail fetch",
                user_id,
            )
            return None

        creds = Credentials(
            token=token_payload.get("access_token"),
            refresh_token=token_payload.get("refresh_token"),
            token_uri=token_payload.get("token_uri"),
            client_id=token_payload.get("client_id"),
            client_secret=token_payload.get("client_secret"),
            scopes=SCOPES,
        )
        if not creds.valid and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Persist refreshed token for future calls.
                token_payload["access_token"] = creds.token
                if creds.expiry:
                    token_payload["expires_at"] = int(creds.expiry.timestamp())
                integration.credentials_json = json.dumps(token_payload)
                integration.config_json = json.dumps({"token": token_payload})
            except Exception as exc:
                logger.warning("Gmail token refresh failed for user_id=%s: %s", user_id, exc)
        logger.info("Gmail auth source=db user_id=%s", user_id)
        return creds


def _build_service(user_id: Optional[int] = None) -> Any:
    """Build a Gmail API service client."""
    settings = get_settings()
    credentials = None
    if user_id is not None:
        credentials = _credentials_from_db_token(user_id)
        if credentials is None:
            # For authenticated app users we do not use token.json in production.
            if settings.is_production:
                logger.info("Gmail auth source=none user_id=%s", user_id)
                return None
            try:
                credentials = _load_credentials_from_file(
                    settings.gmail_token_path,
                    settings.gmail_client_secrets_path,
                )
            except FileNotFoundError:
                return None
    if credentials is None:
        credentials = _load_credentials_from_file(settings.gmail_token_path, settings.gmail_client_secrets_path)
    return build("gmail", "v1", credentials=credentials)


def fetch_messages(max_results: int = 5, user_id: Optional[int] = None) -> List[Dict]:
    """Fetch Gmail messages using stored credentials (legacy broad query)."""

    settings = get_settings()
    try:
        service = _build_service(user_id=user_id)
        if service is None:
            return []
        query = settings.gmail_query
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results, includeSpamTrash=False)
            .execute()
        )
        messages = response.get("messages", [])
        detailed: List[Dict] = []
        for msg_meta in messages:
            msg = service.users().messages().get(userId="me", id=msg_meta["id"], format="full").execute()
            detailed.append(msg)
        return detailed
    except FileNotFoundError as exc:
        logger.warning("Gmail token missing: %s", exc)
        return []
    except HttpError as exc:
        logger.error("Failed to fetch Gmail messages: %s", exc)
        return []
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected Gmail fetch error: %s", exc)
        return []


def fetch_messages_targeted(
    query: str,
    max_results: int = 25,
    known_message_ids: Optional[set] = None,
    user_id: Optional[int] = None,
) -> List[Dict]:
    """Fetch Gmail messages using a targeted query, skipping already-indexed IDs.

    Args:
        query: Gmail API query string (from gmail_query_builder).
        max_results: Max messages to fetch per call.
        known_message_ids: Set of gmail_message_id strings already in the index.

    Returns:
        List of full Gmail message dicts, excluding already-known ones.
    """
    if known_message_ids is None:
        known_message_ids = set()

    try:
        service = _build_service(user_id=user_id)
        if service is None:
            return []
        response = (
            service.users()
            .messages()
            .list(userId="me", q=query, maxResults=max_results, includeSpamTrash=False)
            .execute()
        )
        message_metas = response.get("messages", [])
        new_messages: List[Dict] = []
        for msg_meta in message_metas:
            msg_id = msg_meta["id"]
            if msg_id in known_message_ids:
                continue
            msg = service.users().messages().get(userId="me", id=msg_id, format="full").execute()
            new_messages.append(msg)

        logger.info(
            "Targeted fetch: query=%r, total=%d, new=%d, skipped=%d",
            query[:80], len(message_metas), len(new_messages),
            len(message_metas) - len(new_messages),
        )
        return new_messages
    except FileNotFoundError as exc:
        logger.warning("Gmail token missing: %s", exc)
        return []
    except HttpError as exc:
        logger.error("Failed to fetch Gmail messages: %s", exc)
        return []
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected Gmail fetch error: %s", exc)
        return []


def extract_header(message: Dict[str, Any], header_name: str) -> str:
    """Extract a header value from a Gmail message."""
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            return header.get("value", "")
    return ""


def extract_from_email(message: Dict[str, Any]) -> str:
    """Extract the sender email from a Gmail message From header."""
    from_header = extract_header(message, "From")
    if "<" in from_header and ">" in from_header:
        return from_header.split("<")[1].split(">")[0]
    return from_header


def extract_internal_date(message: Dict[str, Any]) -> Optional[datetime]:
    """Convert Gmail internalDate (ms epoch) to datetime."""
    internal_date_ms = message.get("internalDate")
    if internal_date_ms:
        try:
            return datetime.utcfromtimestamp(int(internal_date_ms) / 1000)
        except (ValueError, OSError):
            pass
    return None


def save_token(token_bytes: bytes) -> None:
    """Persist uploaded Gmail token bytes to configured path."""

    settings = get_settings()
    if settings.is_production:
        logger.info("Skipping local Gmail token file write in production environment")
        return
    settings.gmail_token_path.parent.mkdir(parents=True, exist_ok=True)
    with settings.gmail_token_path.open("wb") as fh:
        fh.write(token_bytes)
    logger.info("Stored Gmail token at %s", settings.gmail_token_path)
