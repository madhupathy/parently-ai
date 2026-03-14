"""Child search profile CRUD routes."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from dependencies import get_current_user
from storage import get_db
from storage.models import Child, ChildSearchProfile, User

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()


class SearchProfileCreate(BaseModel):
    child_id: int
    gmail_query_base: Optional[str] = None
    subject_keywords: Optional[List[str]] = None
    sender_allowlist: Optional[List[str]] = None
    sender_blocklist: Optional[List[str]] = None
    label_whitelist: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None


class SearchProfileUpdate(BaseModel):
    gmail_query_base: Optional[str] = None
    subject_keywords: Optional[List[str]] = None
    sender_allowlist: Optional[List[str]] = None
    sender_blocklist: Optional[List[str]] = None
    label_whitelist: Optional[List[str]] = None
    exclude_keywords: Optional[List[str]] = None


def _serialize_profile(p: ChildSearchProfile) -> Dict[str, Any]:
    return {
        "id": p.id,
        "child_id": p.child_id,
        "gmail_query_base": p.gmail_query_base,
        "subject_keywords": p.subject_keywords(),
        "sender_allowlist": p.sender_allowlist(),
        "sender_blocklist": p.sender_blocklist(),
        "label_whitelist": p.label_whitelist(),
        "exclude_keywords": p.exclude_keywords(),
        "last_sync_at": p.last_sync_at.isoformat() if p.last_sync_at else None,
    }


@router.get("/{child_id}")
def get_search_profile(
    child_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Get the search profile for a child."""
    with db.session_scope() as session:
        child = session.query(Child).filter(
            Child.id == child_id, Child.user_id == current_user.id
        ).first()
        if not child:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")

        profile = session.query(ChildSearchProfile).filter(
            ChildSearchProfile.child_id == child_id
        ).first()

        if not profile:
            return {"ok": True, "profile": None}

        return {"ok": True, "profile": _serialize_profile(profile)}


@router.put("/{child_id}")
def upsert_search_profile(
    child_id: int,
    body: SearchProfileUpdate,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Create or update the search profile for a child."""
    with db.session_scope() as session:
        child = session.query(Child).filter(
            Child.id == child_id, Child.user_id == current_user.id
        ).first()
        if not child:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")

        profile = session.query(ChildSearchProfile).filter(
            ChildSearchProfile.child_id == child_id
        ).first()

        if not profile:
            profile = ChildSearchProfile(child_id=child_id)
            session.add(profile)

        if body.gmail_query_base is not None:
            profile.gmail_query_base = body.gmail_query_base
        if body.subject_keywords is not None:
            profile.subject_keywords_json = json.dumps(body.subject_keywords)
        if body.sender_allowlist is not None:
            profile.sender_allowlist_json = json.dumps(body.sender_allowlist)
        if body.sender_blocklist is not None:
            profile.sender_blocklist_json = json.dumps(body.sender_blocklist)
        if body.label_whitelist is not None:
            profile.label_whitelist_json = json.dumps(body.label_whitelist)
        if body.exclude_keywords is not None:
            profile.exclude_keywords_json = json.dumps(body.exclude_keywords)

        session.flush()
        result = _serialize_profile(profile)

    logger.info("Upserted search profile for child %d (user %d)", child_id, current_user.id)
    return {"ok": True, "profile": result}


@router.delete("/{child_id}")
def delete_search_profile(
    child_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Delete the search profile for a child."""
    with db.session_scope() as session:
        child = session.query(Child).filter(
            Child.id == child_id, Child.user_id == current_user.id
        ).first()
        if not child:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child not found")

        profile = session.query(ChildSearchProfile).filter(
            ChildSearchProfile.child_id == child_id
        ).first()
        if profile:
            session.delete(profile)

    return {"ok": True}
