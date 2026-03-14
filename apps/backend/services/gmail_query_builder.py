"""Build targeted Gmail queries from child search profiles.

Generates Gmail API query strings like:
  newer_than:14d (Vrinda OR "Cedar Ridge Elementary" OR "Ms Johnson")
  -category:promotions

Supports incremental sync via last_sync_at timestamps.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import List, Optional

from storage.models import Child, ChildSearchProfile

logger = logging.getLogger(__name__)


def build_gmail_query(
    child: Child,
    profile: Optional[ChildSearchProfile],
    lookback_days: int = 14,
    since_timestamp: Optional[datetime] = None,
) -> str:
    """Build a Gmail query string for a specific child.

    Priority:
      1. If profile.gmail_query_base is set, use it verbatim (power-user override).
      2. Otherwise, auto-build from child name, school, teacher, keywords, senders.

    Args:
        child: The Child object with name/school/teacher.
        profile: Optional ChildSearchProfile with filtering rules.
        lookback_days: How many days back for initial/broad sync.
        since_timestamp: If set, only fetch messages after this time (incremental).

    Returns:
        A Gmail API-compatible query string.
    """
    # Power-user override
    if profile and profile.gmail_query_base:
        query = profile.gmail_query_base.strip()
        if since_timestamp:
            query += f" after:{int(since_timestamp.timestamp())}"
        return query

    parts: List[str] = []

    # Time window
    if since_timestamp:
        parts.append(f"after:{int(since_timestamp.timestamp())}")
    else:
        parts.append(f"newer_than:{lookback_days}d")

    # Build OR group from child identity + school + teacher
    or_terms: List[str] = []
    if child.name:
        or_terms.append(_quote(child.name))
    if child.school_name:
        or_terms.append(_quote(child.school_name))
    if child.teacher_name:
        for teacher in child.teacher_name.split(","):
            teacher = teacher.strip()
            if teacher:
                or_terms.append(_quote(teacher))

    # Subject keywords from profile
    if profile:
        for kw in profile.subject_keywords():
            or_terms.append(_quote(kw))

    # Sender allowlist — build from: clause
    sender_from: List[str] = []
    if profile:
        for sender in profile.sender_allowlist():
            sender_from.append(f"from:{sender}")

    # Combine identity terms and sender terms with OR
    all_or: List[str] = []
    if or_terms:
        all_or.append("(" + " OR ".join(or_terms) + ")")
    if sender_from:
        all_or.append("(" + " OR ".join(sender_from) + ")")

    if all_or:
        parts.append("(" + " OR ".join(all_or) + ")")

    # Label whitelist
    if profile:
        for label in profile.label_whitelist():
            parts.append(f"label:{label}")

    # Exclude promotions by default
    parts.append("-category:promotions")

    # Exclude keywords
    if profile:
        for excl in profile.exclude_keywords():
            parts.append(f"-{_quote(excl)}")

    # Sender blocklist
    if profile:
        for blocked in profile.sender_blocklist():
            parts.append(f"-from:{blocked}")

    query = " ".join(parts)
    logger.debug("Built Gmail query for child %s: %s", child.name, query)
    return query


def build_default_broad_query(lookback_days: int = 30) -> str:
    """Build a broad query for users without any children configured yet.

    Targets school-related emails broadly.
    """
    return (
        f"newer_than:{lookback_days}d "
        "(school OR elementary OR teacher OR classroom OR homework "
        "OR permission OR field trip OR conference OR picture day "
        "OR report card OR ISD OR district) "
        "-category:promotions -category:social"
    )


def _quote(term: str) -> str:
    """Wrap multi-word terms in quotes for Gmail query."""
    if " " in term:
        return f'"{term}"'
    return term
