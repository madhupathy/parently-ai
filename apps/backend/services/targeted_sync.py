"""Targeted per-child Gmail sync orchestrator.

Flow per child:
  1. Load ChildSearchProfile
  2. Load known gmail_message_ids from GmailMessageIndex
  3. Build targeted Gmail query via gmail_query_builder
  4. Fetch only new messages via gmail.fetch_messages_targeted
  5. Index new messages into GmailMessageIndex
  6. Update last_sync_at on the search profile
  7. Return new messages grouped by child
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from storage import get_db
from storage.models import (
    Child,
    ChildSearchProfile,
    GmailMessageIndex,
    UserPreference,
)
from services import gmail
from services.gmail_query_builder import build_default_broad_query, build_gmail_query

logger = logging.getLogger(__name__)


def sync_gmail_for_user(user_id: int) -> List[Dict[str, Any]]:
    """Run targeted Gmail sync for all children of a user.

    Returns a list of dicts:
      [{"child_id": 1, "child_name": "Vrinda", "messages": [...]}]

    If the user has no children, falls back to a broad school-related query.
    """
    db = get_db()
    results: List[Dict[str, Any]] = []

    # Load children and preferences
    with db.session_scope() as session:
        children = session.query(Child).filter(Child.user_id == user_id).all()
        children_data: List[Dict[str, Any]] = []
        for c in children:
            profile = session.query(ChildSearchProfile).filter(
                ChildSearchProfile.child_id == c.id
            ).first()
            children_data.append({
                "id": c.id,
                "name": c.name,
                "school_name": c.school_name,
                "teacher_name": c.teacher_name,
                "grade": c.grade,
                "profile": _copy_profile(profile) if profile else None,
                "last_sync_at": profile.last_sync_at if profile else None,
            })

        pref = session.query(UserPreference).filter(
            UserPreference.user_id == user_id
        ).first()
        lookback_days = pref.lookback_days if pref else 14

    if not children_data:
        # No children — broad school query
        broad_messages = _fetch_broad(user_id, lookback_days)
        if broad_messages:
            results.append({
                "child_id": None,
                "child_name": "General",
                "messages": broad_messages,
            })
        return results

    # Per-child targeted sync
    for child_data in children_data:
        child_id = child_data["id"]
        child_name = child_data["name"]

        try:
            new_messages = _sync_child(user_id, child_data, lookback_days)
            if new_messages:
                results.append({
                    "child_id": child_id,
                    "child_name": child_name,
                    "messages": new_messages,
                })
                logger.info(
                    "Synced %d new messages for child %s (id=%d)",
                    len(new_messages), child_name, child_id,
                )
        except Exception as exc:
            logger.error("Sync failed for child %s (id=%d): %s", child_name, child_id, exc)

    return results


def _sync_child(
    user_id: int,
    child_data: Dict[str, Any],
    lookback_days: int,
) -> List[Dict[str, Any]]:
    """Sync Gmail for a single child. Returns list of new message dicts."""
    db = get_db()
    child_id = child_data["id"]

    # Load known message IDs for dedup
    with db.session_scope() as session:
        known_rows = session.query(GmailMessageIndex.gmail_message_id).filter(
            GmailMessageIndex.user_id == user_id,
            GmailMessageIndex.child_id == child_id,
        ).all()
        known_ids = {row[0] for row in known_rows}

    # Build a transient Child-like object for the query builder
    child_obj = _make_child_obj(child_data)
    profile_obj = child_data.get("profile")
    since = child_data.get("last_sync_at")

    query = build_gmail_query(
        child=child_obj,
        profile=profile_obj,
        lookback_days=lookback_days,
        since_timestamp=since,
    )

    # Fetch new messages
    new_messages = gmail.fetch_messages_targeted(
        query=query,
        max_results=25,
        known_message_ids=known_ids,
    )

    if not new_messages:
        return []

    # Index new messages
    _index_messages(user_id, child_id, new_messages)

    # Update last_sync_at
    _update_sync_timestamp(child_id)

    return new_messages


def _fetch_broad(user_id: int, lookback_days: int) -> List[Dict[str, Any]]:
    """Broad school-related fetch for users without children profiles."""
    db = get_db()

    with db.session_scope() as session:
        known_rows = session.query(GmailMessageIndex.gmail_message_id).filter(
            GmailMessageIndex.user_id == user_id,
            GmailMessageIndex.child_id.is_(None),
        ).all()
        known_ids = {row[0] for row in known_rows}

    query = build_default_broad_query(lookback_days=lookback_days)
    new_messages = gmail.fetch_messages_targeted(
        query=query,
        max_results=25,
        known_message_ids=known_ids,
    )

    if new_messages:
        _index_messages(user_id, None, new_messages)

    return new_messages


def _index_messages(
    user_id: int,
    child_id: Optional[int],
    messages: List[Dict[str, Any]],
) -> None:
    """Save fetched messages into GmailMessageIndex for dedup and tracking."""
    db = get_db()
    with db.session_scope() as session:
        for msg in messages:
            msg_id = msg.get("id", "")
            # Skip if somehow already exists
            existing = session.query(GmailMessageIndex).filter(
                GmailMessageIndex.gmail_message_id == msg_id
            ).first()
            if existing:
                continue

            subject = gmail.extract_header(msg, "Subject")
            from_email = gmail.extract_from_email(msg)
            internal_date = gmail.extract_internal_date(msg)
            snippet = msg.get("snippet", "")
            label_ids = msg.get("labelIds", [])

            index_entry = GmailMessageIndex(
                user_id=user_id,
                child_id=child_id,
                gmail_message_id=msg_id,
                thread_id=msg.get("threadId"),
                internal_date=internal_date,
                from_email=from_email,
                subject=subject,
                snippet=snippet,
                label_ids_json=json.dumps(label_ids),
                fetched_at=datetime.utcnow(),
            )
            session.add(index_entry)

        logger.info("Indexed %d messages (user=%d, child=%s)", len(messages), user_id, child_id)


def _update_sync_timestamp(child_id: int) -> None:
    """Update last_sync_at on the child's search profile."""
    db = get_db()
    with db.session_scope() as session:
        profile = session.query(ChildSearchProfile).filter(
            ChildSearchProfile.child_id == child_id
        ).first()
        if profile:
            profile.last_sync_at = datetime.utcnow()


def _copy_profile(profile: ChildSearchProfile) -> Optional[ChildSearchProfile]:
    """Create a detached copy of a ChildSearchProfile for use outside session."""
    if not profile:
        return None
    from sqlalchemy.orm import make_transient
    # We need a simple object that has the same attributes
    cp = ChildSearchProfile(
        child_id=profile.child_id,
        gmail_query_base=profile.gmail_query_base,
        subject_keywords_json=profile.subject_keywords_json,
        sender_allowlist_json=profile.sender_allowlist_json,
        sender_blocklist_json=profile.sender_blocklist_json,
        label_whitelist_json=profile.label_whitelist_json,
        exclude_keywords_json=profile.exclude_keywords_json,
        last_sync_at=profile.last_sync_at,
    )
    make_transient(cp)
    return cp


class _ChildStub:
    """Lightweight stand-in for Child used by the query builder."""
    def __init__(self, name: str, school_name: Optional[str], teacher_name: Optional[str]):
        self.name = name
        self.school_name = school_name
        self.teacher_name = teacher_name


def _make_child_obj(child_data: Dict[str, Any]) -> _ChildStub:
    return _ChildStub(
        name=child_data.get("name", ""),
        school_name=child_data.get("school_name"),
        teacher_name=child_data.get("teacher_name"),
    )
