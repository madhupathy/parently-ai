"""Auth routes — user lookup/creation from NextAuth JWT."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from dependencies import get_current_user
from storage import get_db
from storage.models import Child, User, UserEntitlement, UserIntegration, UserPreference

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()


class SessionUser(BaseModel):
    email: str
    name: Optional[str] = None
    image: Optional[str] = None
    provider: str = "google"
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token_expires_at: Optional[int] = None
    granted_scopes: Optional[str] = None


@router.post("/sync")
def sync_user(
    payload: SessionUser,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update user profile from the NextAuth session (JWT-protected)."""

    def _upsert_google_integration(
        session: Any,
        *,
        user_id: int,
        provider: str,
        scope: str,
        payload: SessionUser,
    ) -> None:
        row = (
            session.query(UserIntegration)
            .filter(UserIntegration.user_id == user_id, UserIntegration.provider == provider)
            .first()
        )
        token_payload = {}
        if payload.access_token:
            token_payload["access_token"] = payload.access_token
        if payload.refresh_token:
            token_payload["refresh_token"] = payload.refresh_token
        if payload.access_token_expires_at:
            token_payload["expires_at"] = payload.access_token_expires_at

        if row:
            row.platform = "gmail" if provider == "gmail" else "gdrive"
            row.granted_scopes = payload.granted_scopes or row.granted_scopes
            if token_payload:
                existing = {}
                if row.credentials_json:
                    try:
                        existing = json.loads(row.credentials_json)
                    except Exception:
                        existing = {}
                existing.update(token_payload)
                row.credentials_json = json.dumps(existing)
                row.config_json = json.dumps({"token": existing})
            row.status = "connected" if payload.granted_scopes and scope in payload.granted_scopes else "scope_missing"
            return

        if not token_payload and not payload.granted_scopes:
            return
        session.add(
            UserIntegration(
                user_id=user_id,
                platform="gmail" if provider == "gmail" else "gdrive",
                provider=provider,
                credentials_json=json.dumps(token_payload) if token_payload else None,
                config_json=json.dumps({"token": token_payload}) if token_payload else None,
                granted_scopes=payload.granted_scopes,
                status="connected" if payload.granted_scopes and scope in payload.granted_scopes else "scope_missing",
            )
        )

    with db.session_scope() as session:
        user = session.query(User).filter(User.id == current_user.id).first()
        if user:
            if payload.name and payload.name != user.name:
                user.name = payload.name
            if payload.image and payload.image != user.avatar_url:
                user.avatar_url = payload.image
            if payload.provider and payload.provider != user.provider:
                user.provider = payload.provider

            # Persist Google OAuth tokens/scopes into integration storage for backend Gmail/Drive access.
            if payload.provider == "google":
                _upsert_google_integration(
                    session,
                    user_id=user.id,
                    provider="gmail",
                    scope="https://www.googleapis.com/auth/gmail.readonly",
                    payload=payload,
                )
                _upsert_google_integration(
                    session,
                    user_id=user.id,
                    provider="google_drive",
                    scope="https://www.googleapis.com/auth/drive.readonly",
                    payload=payload,
                )

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
        entitlement_data = {
            "plan": entitlement.plan,
            "digests_remaining": entitlement.digests_remaining,
            "premium_active": entitlement.premium_active,
        } if entitlement else {
            "plan": "FREE",
            "digests_remaining": 30,
            "premium_active": False,
        }

        children = session.query(Child).filter(Child.user_id == current_user.id).all()
        children_data = [
            {"id": c.id, "name": c.name, "grade": c.grade, "school_name": c.school_name}
            for c in children
        ]
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
        "entitlement": entitlement_data,
        "children": children_data,
    }


@router.post("/onboarding-complete")
def complete_onboarding(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Mark onboarding as complete."""
    with db.session_scope() as session:
        user = session.query(User).filter(User.id == current_user.id).first()
        if user:
            user.onboarding_complete = True
    return {"ok": True}
