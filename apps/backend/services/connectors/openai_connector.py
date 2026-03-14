"""OpenAI / ChatGPT connector — lets users provide their own API key for digest summarization.

This connector doesn't fetch external data like the others. Instead, it stores
the user's OpenAI API key so the digest compose step can use it for
personalized GPT-4o-mini summarization instead of the system-wide key.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseConnector, DigestItem

logger = logging.getLogger(__name__)


class OpenAIConnector(BaseConnector):
    """Validates and stores a user-provided OpenAI API key."""

    platform = "openai"

    def __init__(self) -> None:
        self._api_key: Optional[str] = None
        self._model: str = "gpt-4o-mini"

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Validate the API key by making a lightweight models.list call."""
        api_key = credentials.get("api_key", "").strip()
        if not api_key or not api_key.startswith("sk-"):
            logger.warning("OpenAI connector: invalid API key format")
            return False

        self._api_key = api_key
        self._model = credentials.get("model", "gpt-4o-mini")

        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            # Lightweight validation — list models (costs nothing)
            client.models.list()
            logger.info("OpenAI connector: API key validated successfully")
            return True
        except Exception as exc:
            logger.warning("OpenAI connector: key validation failed: %s", exc)
            return False

    def fetch_updates(self, since: Optional[datetime] = None) -> List[DigestItem]:
        """OpenAI connector doesn't fetch data — it provides the LLM key.

        Returns an empty list. The actual usage happens in compose_digest_node
        which reads the user's OpenAI config from their integration row.
        """
        return []

    @property
    def api_key(self) -> Optional[str]:
        return self._api_key

    @property
    def model(self) -> str:
        return self._model
