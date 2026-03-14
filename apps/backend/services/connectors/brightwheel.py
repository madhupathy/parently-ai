"""Brightwheel connector — fetch daily reports and activities.

Brightwheel exposes a JSON API for parents. This connector authenticates
with email/password, then fetches daily activity reports, photos, and
messages for the authenticated parent's students.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

from .base import BaseConnector, DigestItem

logger = logging.getLogger(__name__)

BW_API_BASE = "https://schools.mybrightwheel.com/api/v1"


class BrightwheelConnector(BaseConnector):
    """Fetch daily reports from Brightwheel's parent API."""

    platform = "brightwheel"

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._student_ids: List[str] = []
        self._client: Optional[httpx.Client] = None

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Login to Brightwheel with email/password."""
        email = credentials.get("email")
        password = credentials.get("password")

        if not email or not password:
            logger.warning("Brightwheel connector: missing credentials")
            return False

        try:
            client = httpx.Client(timeout=30.0)
            resp = client.post(
                f"{BW_API_BASE}/sessions",
                json={"user": {"email": email, "password": password}},
            )
            resp.raise_for_status()
            data = resp.json()

            self._token = data.get("token") or data.get("user", {}).get("auth_token")
            if not self._token:
                logger.warning("Brightwheel: no token in auth response")
                client.close()
                return False

            client.headers["Authorization"] = f"Bearer {self._token}"
            self._client = client

            # Fetch student IDs for this parent
            self._student_ids = self._fetch_student_ids()
            logger.info("Brightwheel: authenticated, %d students", len(self._student_ids))
            return True
        except httpx.HTTPStatusError as exc:
            logger.warning("Brightwheel auth failed (HTTP %d): %s", exc.response.status_code, exc)
            return False
        except Exception as exc:
            logger.error("Brightwheel auth error: %s", exc)
            return False

    def _fetch_student_ids(self) -> List[str]:
        """Get the list of student IDs for the authenticated parent."""
        try:
            resp = self._client.get(f"{BW_API_BASE}/students")  # type: ignore[union-attr]
            resp.raise_for_status()
            students = resp.json().get("students", [])
            return [s["id"] for s in students if s.get("id")]
        except Exception as exc:
            logger.debug("Failed to fetch Brightwheel students: %s", exc)
            return []

    def fetch_updates(self, since: Optional[datetime] = None) -> List[DigestItem]:
        """Fetch daily reports, activities, and photos for all students."""
        if not self._client or not self._token:
            logger.warning("Brightwheel connector not authenticated")
            return []

        items: List[DigestItem] = []
        for student_id in self._student_ids:
            items.extend(self._fetch_activities(student_id, since))
        logger.info("Brightwheel: fetched %d items", len(items))
        return items

    def _fetch_activities(self, student_id: str, since: Optional[datetime] = None) -> List[DigestItem]:
        """Fetch activity feed for a single student."""
        try:
            params: Dict[str, Any] = {"page_size": 20}
            if since:
                params["after"] = since.isoformat()

            resp = self._client.get(  # type: ignore[union-attr]
                f"{BW_API_BASE}/students/{student_id}/activities",
                params=params,
            )
            resp.raise_for_status()
            activities = resp.json().get("activities", [])

            items: List[DigestItem] = []
            for act in activities:
                act_type = act.get("type", "activity")
                text = act.get("note", "") or act.get("comment", "") or ""
                title = self._activity_title(act_type, act)
                tags = self._activity_tags(act_type)
                timestamp = act.get("created_at", "")

                items.append(DigestItem(
                    source="brightwheel",
                    title=title,
                    body=text[:500] if text else f"{act_type} recorded",
                    tags=tags,
                    timestamp=timestamp,
                    raw=act,
                ))
            return items
        except Exception as exc:
            logger.debug("Brightwheel activities fetch failed for %s: %s", student_id, exc)
            return []

    @staticmethod
    def _activity_title(act_type: str, act: Dict[str, Any]) -> str:
        """Generate a human-readable title from activity type."""
        titles = {
            "diaper": "Diaper Change",
            "nap": "Nap Time",
            "meal": "Meal/Snack",
            "photo": "New Photo",
            "incident": "Incident Report",
            "note": "Teacher Note",
            "check_in": "Check-in",
            "check_out": "Check-out",
            "learning": "Learning Activity",
        }
        return titles.get(act_type, act_type.replace("_", " ").title())

    @staticmethod
    def _activity_tags(act_type: str) -> List[str]:
        """Map activity type to tags."""
        tag_map = {
            "diaper": ["care"],
            "nap": ["care"],
            "meal": ["care"],
            "photo": ["activity"],
            "incident": ["action"],
            "note": ["message"],
            "check_in": ["attendance"],
            "check_out": ["attendance"],
            "learning": ["activity"],
        }
        return tag_map.get(act_type, ["general"])

    def __del__(self) -> None:
        if self._client:
            try:
                self._client.close()
            except Exception:
                pass
