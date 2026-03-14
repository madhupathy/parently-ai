"""ClassDojo connector — parses ClassDojo notification emails from Gmail.

ClassDojo sends notification emails for classroom updates, teacher messages,
and activity reports. This connector filters Gmail for those senders and
extracts structured digest items from the email content.
"""

from __future__ import annotations

import base64
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from .base import BaseConnector, DigestItem

logger = logging.getLogger(__name__)

CLASSDOJO_SENDERS = [
    "noreply@classdojo.com",
    "notifications@classdojo.com",
    "hello@classdojo.com",
]

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


class ClassDojoConnector(BaseConnector):
    """Extract ClassDojo updates by filtering Gmail for ClassDojo sender addresses."""

    platform = "classdojo"

    def __init__(self) -> None:
        self._service: Optional[Any] = None

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Build Gmail service from OAuth token to filter ClassDojo emails."""
        token_info = credentials.get("token") or credentials
        if not token_info:
            logger.warning("ClassDojo connector: no Gmail credentials")
            return False

        try:
            creds = Credentials.from_authorized_user_info(token_info, scopes=GMAIL_SCOPES)
            if not creds.valid and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            self._service = build("gmail", "v1", credentials=creds)
            return True
        except Exception as exc:
            logger.error("ClassDojo auth failed: %s", exc)
            return False

    def fetch_updates(self, since: Optional[datetime] = None) -> List[DigestItem]:
        """Filter Gmail for ClassDojo sender emails and parse them."""
        if not self._service:
            logger.warning("ClassDojo connector not authenticated")
            return []

        try:
            sender_query = " OR ".join(f"from:{s}" for s in CLASSDOJO_SENDERS)
            query = f"({sender_query})"
            if since:
                query += f" after:{since.strftime('%Y/%m/%d')}"
            else:
                query += " newer_than:7d"

            response = self._service.users().messages().list(
                userId="me", q=query, maxResults=15,
            ).execute()

            items: List[DigestItem] = []
            for msg_meta in response.get("messages", []):
                msg = self._service.users().messages().get(
                    userId="me", id=msg_meta["id"], format="full",
                ).execute()
                item = self._parse_message(msg)
                if item:
                    items.append(item)

            logger.info("ClassDojo: fetched %d items from Gmail", len(items))
            return items
        except Exception as exc:
            logger.error("ClassDojo fetch failed: %s", exc)
            return []

    def _parse_message(self, msg: Dict[str, Any]) -> Optional[DigestItem]:
        """Extract a DigestItem from a Gmail message."""
        try:
            headers = msg.get("payload", {}).get("headers", [])
            subject = ""
            date_str = ""
            for h in headers:
                if h["name"].lower() == "subject":
                    subject = h["value"]
                elif h["name"].lower() == "date":
                    date_str = h["value"]

            body = self._extract_body(msg.get("payload", {}))
            # Clean HTML tags from body
            body = re.sub(r"<[^>]+>", " ", body)
            body = re.sub(r"\s+", " ", body).strip()

            # Classify the type of ClassDojo notification
            tags = self._classify_tags(subject, body)

            return DigestItem(
                source="classdojo",
                title=subject or "ClassDojo Update",
                body=body[:500],
                due_date=None,
                tags=tags,
                timestamp=date_str,
                raw={"message_id": msg.get("id"), "subject": subject},
            )
        except Exception as exc:
            logger.debug("Failed to parse ClassDojo message: %s", exc)
            return None

    def _extract_body(self, payload: Dict[str, Any]) -> str:
        """Recursively extract text body from Gmail payload."""
        if payload.get("mimeType", "").startswith("text/"):
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")

        for part in payload.get("parts", []):
            text = self._extract_body(part)
            if text:
                return text
        return ""

    @staticmethod
    def _classify_tags(subject: str, body: str) -> List[str]:
        """Classify ClassDojo notification type from subject/body."""
        combined = (subject + " " + body).lower()
        tags: List[str] = []
        if any(w in combined for w in ("message", "sent you", "replied")):
            tags.append("message")
        if any(w in combined for w in ("story", "photo", "posted")):
            tags.append("activity")
        if any(w in combined for w in ("event", "conference", "meeting")):
            tags.append("event")
        if any(w in combined for w in ("report", "behavior", "points")):
            tags.append("report")
        return tags or ["general"]
