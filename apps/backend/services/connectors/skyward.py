"""Skyward Family Access connector.

Skyward Family Access uses a form-based login flow. This connector
authenticates via httpx, then scrapes the gradebook and message
pages to extract digest items.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import BaseConnector, DigestItem

logger = logging.getLogger(__name__)


class SkywardConnector(BaseConnector):
    """Fetch grades, attendance, and messages from Skyward Family Access."""

    platform = "skyward"

    def __init__(self) -> None:
        self._base_url: Optional[str] = None
        self._client: Optional[httpx.Client] = None

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Login to Skyward with username/password via form POST."""
        self._base_url = credentials.get("url", "").rstrip("/")
        username = credentials.get("username")
        password = credentials.get("password")

        if not all([self._base_url, username, password]):
            logger.warning("Skyward connector: missing credentials")
            return False

        try:
            client = httpx.Client(follow_redirects=True, timeout=30.0)
            # Step 1: GET login page to obtain any hidden fields / session cookies
            login_url = f"{self._base_url}/skyward/logon.html"
            login_page = client.get(login_url)
            login_page.raise_for_status()

            # Step 2: POST credentials
            login_post_url = f"{self._base_url}/skyward/Logon.aspx"
            payload = {
                "codeType": "tryLogin",
                "login": username,
                "password": password,
                "Browser": "Chrome",
            }
            resp = client.post(login_post_url, data=payload)
            resp.raise_for_status()

            # Skyward returns a redirect or session cookie on success
            if "SessionID" in client.cookies or "sfhome" in resp.text.lower():
                self._client = client
                logger.info("Skyward: authenticated as %s", username)
                return True
            else:
                logger.warning("Skyward: login failed — no session cookie")
                client.close()
                return False
        except Exception as exc:
            logger.error("Skyward auth error: %s", exc)
            return False

    def fetch_updates(self, since: Optional[datetime] = None) -> List[DigestItem]:
        """Scrape gradebook and messages from Skyward."""
        if not self._client or not self._base_url:
            logger.warning("Skyward connector not authenticated")
            return []

        items: List[DigestItem] = []
        items.extend(self._fetch_grades())
        items.extend(self._fetch_messages())
        logger.info("Skyward: fetched %d items", len(items))
        return items

    def _fetch_grades(self) -> List[DigestItem]:
        """Scrape the gradebook page for recent grade updates."""
        try:
            url = f"{self._base_url}/skyward/Gradebook.aspx"
            resp = self._client.get(url)  # type: ignore[union-attr]
            resp.raise_for_status()
            text = resp.text

            items: List[DigestItem] = []
            # Parse grade rows — Skyward uses table-based HTML
            rows = re.findall(
                r'<tr[^>]*class="[^"]*sg-asp-table-data-row[^"]*"[^>]*>(.*?)</tr>',
                text, re.DOTALL,
            )
            for row in rows[:10]:
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
                cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
                if len(cells) >= 3:
                    course = cells[0]
                    grade = cells[-1]
                    items.append(DigestItem(
                        source="skyward",
                        title=f"Grade Update: {course}",
                        body=f"Current grade: {grade}",
                        tags=["grade"],
                        raw={"course": course, "grade": grade},
                    ))
            return items
        except Exception as exc:
            logger.debug("Skyward grade scrape failed: %s", exc)
            return []

    def _fetch_messages(self) -> List[DigestItem]:
        """Scrape the messages/inbox page."""
        try:
            url = f"{self._base_url}/skyward/Message.aspx"
            resp = self._client.get(url)  # type: ignore[union-attr]
            resp.raise_for_status()
            text = resp.text

            items: List[DigestItem] = []
            rows = re.findall(
                r'<tr[^>]*class="[^"]*message-row[^"]*"[^>]*>(.*?)</tr>',
                text, re.DOTALL,
            )
            for row in rows[:10]:
                cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
                cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
                if len(cells) >= 2:
                    subject = cells[0]
                    preview = cells[1] if len(cells) > 1 else ""
                    items.append(DigestItem(
                        source="skyward",
                        title=subject,
                        body=preview[:300],
                        tags=["message"],
                        raw={"subject": subject},
                    ))
            return items
        except Exception as exc:
            logger.debug("Skyward message scrape failed: %s", exc)
            return []

    def __del__(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
