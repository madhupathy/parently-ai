"""Abstract base class for platform connectors."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DigestItem:
    """Normalized item from any connector source."""

    source: str
    title: str
    body: str
    due_date: Optional[str] = None
    priority: str = "low"
    tags: List[str] = field(default_factory=lambda: ["general"])
    timestamp: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)


class BaseConnector(ABC):
    """Abstract connector that all platform adapters must implement."""

    platform: str = "unknown"

    @abstractmethod
    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Validate and store credentials. Return True if successful."""
        ...

    @abstractmethod
    def fetch_updates(self, since: Optional[datetime] = None) -> List[DigestItem]:
        """Fetch new items since the given timestamp."""
        ...

    def test_connection(self) -> bool:
        """Quick health check. Default tries fetch with limit."""
        try:
            items = self.fetch_updates()
            return True
        except Exception as exc:
            logger.warning("Connection test failed for %s: %s", self.platform, exc)
            return False
