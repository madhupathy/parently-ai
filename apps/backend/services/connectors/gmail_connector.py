"""Gmail connector — wraps the existing gmail service into the BaseConnector interface."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseConnector, DigestItem

logger = logging.getLogger(__name__)


class GmailConnector(BaseConnector):
    """Fetch school-related emails from Gmail using stored OAuth tokens."""

    platform = "gmail"

    def __init__(self) -> None:
        self._query: Optional[str] = None
        self._max_results: int = 10
        self._user_id: Optional[int] = None

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Store connector config and caller context for Gmail fetches."""
        self._query = credentials.get("query", "in:inbox newer_than:7d")
        self._max_results = credentials.get("max_results", 10)
        self._user_id = credentials.get("user_id")
        return True

    def fetch_updates(self, since: Optional[datetime] = None) -> List[DigestItem]:
        """Fetch Gmail messages and convert to DigestItems."""
        try:
            from services.gmail import fetch_messages

            if self._user_id is None:
                logger.warning("Gmail connector: missing user_id, skipping fetch")
                return []
            messages = fetch_messages(max_results=self._max_results, user_id=self._user_id)
            items: List[DigestItem] = []

            for message in messages:
                snippet = message.get("snippet") or ""
                subject = _extract_header(message, "Subject")
                date_str = _extract_header(message, "Date")
                sender = _extract_header(message, "From")

                if not subject and not snippet:
                    continue

                tags = _classify_email(subject, snippet)

                items.append(DigestItem(
                    source="gmail",
                    title=subject or "Email Update",
                    body=snippet[:500],
                    due_date=None,
                    tags=tags,
                    timestamp=date_str,
                    raw={"from": sender, "subject": subject},
                ))

            logger.info("Gmail connector: fetched %d items", len(items))
            return items
        except Exception as exc:
            logger.error("Gmail connector fetch failed: %s", exc)
            return []


def _extract_header(message: Dict[str, Any], header_name: str) -> str:
    """Extract a header value from a Gmail API message."""
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    for header in headers:
        if header.get("name", "").lower() == header_name.lower():
            return header.get("value", "")
    return ""


def _classify_email(subject: str, body: str) -> List[str]:
    """Classify email content into tags."""
    combined = (subject + " " + body).lower()
    tags: List[str] = []
    if any(w in combined for w in ("due", "deadline", "submit", "permission", "sign")):
        tags.append("action")
    if any(w in combined for w in ("payment", "fee", "tuition", "invoice")):
        tags.append("finance")
    if any(w in combined for w in ("event", "field trip", "performance", "conference", "meeting")):
        tags.append("event")
    return tags or ["general"]
