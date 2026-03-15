"""Auth routes — user lookup/creation from NextAuth JWT."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from config import get_settings
from dependencies import get_current_user
from services.integration_state import DRIVE_SCOPE, GMAIL_SCOPE, parse_scopes
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
    token_uri: Optional[str] = None


@router.post("/sync")
def sync_user(
    payload: SessionUser,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update user profile from the NextAuth session (JWT-protected)."""
    settings = get_settings()

    def _oauth_payload(payload: SessionUser, existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        data = dict(existing or {})
        if payload.access_token:
            data["access_token"] = payload.access_token
            data["token"] = payload.access_token
        if payload.refresh_token:
            data["refresh_token"] = payload.refresh_token
        if payload.access_token_expires_at:
            data["expires_at"] = payload.access_token_expires_at
        data["token_uri"] = payload.token_uri or data.get("token_uri") or "https://oauth2.googleapis.com/token"
        data["client_id"] = data.get("client_id") or settings.google_client_id
        data["client_secret"] = data.get("client_secret") or settings.google_client_secret
        if payload.granted_scopes:
            data["scopes"] = [scope for scope in payload.granted_scopes.split(" ") if scope]
        return data

    def _oauth_ready(token_payload: Dict[str, Any]) -> bool:
        required = ("access_token", "refresh_token", "token_uri", "client_id", "client_secret")
        return all(bool(token_payload.get(key)) for key in required)

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
        scopes = parse_scopes(payload.granted_scopes)
        has_scope = scope in scopes
        token_payload: Dict[str, Any] = {}

        if row:
            existing_token: Dict[str, Any] = {}
            if row.credentials_json:
                try:
                    existing_token = json.loads(row.credentials_json)
                except Exception:
                    existing_token = {}
            token_payload = _oauth_payload(payload, existing=existing_token)

            row.provider = provider
            row.platform = "gmail" if provider == "gmail" else "gdrive"
            row.granted_scopes = payload.granted_scopes or row.granted_scopes
            row.credentials_json = json.dumps(token_payload)
            cfg: Dict[str, Any] = {}
            if row.config_json:
                try:
                    cfg = json.loads(row.config_json)
                except Exception:
                    cfg = {}
            cfg["token"] = token_payload
            cfg["oauth"] = token_payload
            row.config_json = json.dumps(cfg)

            if provider == "google_drive":
                has_folder = bool((cfg.get("folder_id") or "").strip())
                row.status = "connected" if has_scope and _oauth_ready(token_payload) and has_folder else "scope_missing"
            else:
                row.status = "connected" if has_scope and _oauth_ready(token_payload) else "scope_missing"
            return

        token_payload = _oauth_payload(payload)
        if not token_payload and not payload.granted_scopes:
            return
        status_value = "scope_missing"
        if provider == "gmail":
            status_value = "connected" if has_scope and _oauth_ready(token_payload) else "scope_missing"
        session.add(
            UserIntegration(
                user_id=user_id,
                platform="gmail" if provider == "gmail" else "gdrive",
                provider=provider,
                credentials_json=json.dumps(token_payload) if token_payload else None,
                config_json=json.dumps({"token": token_payload, "oauth": token_payload}) if token_payload else None,
                granted_scopes=payload.granted_scopes,
                status=status_value,
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
                    scope=GMAIL_SCOPE,
                    payload=payload,
                )
                _upsert_google_integration(
                    session,
                    user_id=user.id,
                    provider="google_drive",
                    scope=DRIVE_SCOPE,
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
