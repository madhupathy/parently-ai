"""Auth routes — user lookup/creation from NextAuth JWT."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from dependencies import get_current_user
from storage import get_db
from storage.models import Child, User, UserEntitlement, UserPreference

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()


class SessionUser(BaseModel):
    email: str
    name: Optional[str] = None
    image: Optional[str] = None
    provider: str = "google"


@router.post("/sync")
def sync_user(
    payload: SessionUser,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update user profile from the NextAuth session (JWT-protected)."""
    with db.session_scope() as session:
        user = session.query(User).filter(User.id == current_user.id).first()
        if user:
            if payload.name and payload.name != user.name:
                user.name = payload.name
            if payload.image and payload.image != user.avatar_url:
                user.avatar_url = payload.image

        return {
            "ok": True,
            "user": {
                "id": current_user.id,
                "email": current_user.email,
                "name": current_user.name,
                "provider": current_user.provider,
            },
        }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return the current user profile from the JWT."""
    with db.session_scope() as session:
        entitlement = session.query(UserEntitlement).filter(
            UserEntitlement.user_id == current_user.id
        ).first()

        children = session.query(Child).filter(Child.user_id == current_user.id).all()
        user_obj = session.query(User).filter(User.id == current_user.id).first()
        onboarding_done = user_obj.onboarding_complete if user_obj else False

    return {
        "ok": True,
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "name": current_user.name,
            "avatar_url": current_user.avatar_url,
            "provider": current_user.provider,
            "onboarding_complete": onboarding_done,
        },
        "entitlement": {
            "plan": entitlement.plan if entitlement else "FREE",
            "digests_remaining": entitlement.digests_remaining if entitlement else 30,
            "premium_active": entitlement.premium_active if entitlement else False,
        } if entitlement else None,
        "children": [
            {"id": c.id, "name": c.name, "grade": c.grade, "school_name": c.school_name}
            for c in children
        ],
    }


@router.post("/onboarding-complete")
def complete_onboarding(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Mark onboarding as complete."""
    with db.session_scope() as session:
        user = session.query(User).filter(User.id == current_user.id).first()
        if user:
            user.onboarding_complete = True
    return {"ok": True}
