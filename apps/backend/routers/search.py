"""Full-text search across digest history."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query

from dependencies import get_current_user
from storage import get_db
from storage.models import Digest, User

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()


def _excerpt(text: str, query: str, context: int = 120) -> str:
    """Return a short excerpt of text around the first occurrence of query."""
    if not text or not query:
        return text[:context] if text else ""
    lower_text = text.lower()
    lower_query = query.lower()
    idx = lower_text.find(lower_query)
    if idx == -1:
        return text[:context]
    start = max(0, idx - context // 2)
    end = min(len(text), idx + len(query) + context // 2)
    excerpt = text[start:end]
    if start > 0:
        excerpt = "..." + excerpt
    if end < len(text):
        excerpt = excerpt + "..."
    return excerpt


def _digest_matches(digest: Digest, query: str, child_name: Optional[str]) -> Optional[Dict[str, Any]]:
    """Return match info if this digest matches the search criteria, else None."""
    q_lower = query.lower()

    # Filter by child_name if provided
    if child_name:
        cn_lower = child_name.lower()
        # Check items_json for child_name
        items: List[Dict[str, Any]] = []
        try:
            items = json.loads(digest.items_json) if digest.items_json else []
        except (json.JSONDecodeError, TypeError):
            items = []
        child_items = [i for i in items if cn_lower in (i.get("child_name") or "").lower()]
        if not child_items:
            return None
        items = child_items

    # Full-text match in summary_md and items
    matched_in: List[str] = []
    excerpt_text = ""

    if digest.summary_md and q_lower in digest.summary_md.lower():
        matched_in.append("summary")
        excerpt_text = _excerpt(digest.summary_md, query)

    try:
        items_list: List[Dict[str, Any]] = json.loads(digest.items_json) if digest.items_json else []
    except (json.JSONDecodeError, TypeError):
        items_list = []

    matching_items = []
    for item in items_list:
        subject = (item.get("subject") or "").lower()
        body = (item.get("body") or "").lower()
        if q_lower in subject or q_lower in body:
            matching_items.append(item)
            if not excerpt_text:
                excerpt_text = _excerpt(item.get("body") or item.get("subject") or "", query)

    if matching_items:
        matched_in.append("items")

    if not matched_in:
        return None

    return {
        "id": digest.id,
        "digest_date": digest.digest_date,
        "created_at": digest.created_at.isoformat(),
        "matched_in": matched_in,
        "excerpt": excerpt_text,
        "matching_item_count": len(matching_items),
        "matching_items": [
            {
                "subject": item.get("subject", ""),
                "body": (item.get("body") or "")[:200],
                "child_name": item.get("child_name"),
                "tags": item.get("tags", []),
                "due_date": item.get("due_date"),
            }
            for item in matching_items[:5]  # cap at 5 preview items
        ],
    }


@router.get("/digests")
def search_digests(
    q: str = Query(..., min_length=1, description="Search term"),
    child_name: Optional[str] = Query(None, description="Filter by child name"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Full-text search across all digest content (summary and items)."""
    with db.session_scope() as session:
        # Load all digests for this user ordered by date desc
        # For small to medium datasets ILIKE-style in Python is fine.
        # For large deployments, replace with a proper PostgreSQL tsvector query.
        digests = (
            session.query(Digest)
            .filter(Digest.user_id == current_user.id)
            .order_by(Digest.digest_date.desc().nullslast(), Digest.created_at.desc())
            .all()
        )

    results: List[Dict[str, Any]] = []
    for digest in digests:
        match = _digest_matches(digest, q, child_name)
        if match:
            results.append(match)

    total = len(results)
    paginated = results[offset : offset + limit]

    return {
        "ok": True,
        "query": q,
        "child_name": child_name,
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": paginated,
    }
