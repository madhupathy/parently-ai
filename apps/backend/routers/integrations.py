"""Integration management routes."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from config import get_settings
from dependencies import get_current_user
from services.gmail import save_token
from storage import get_db
from storage.models import User, UserIntegration

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()

SUPPORTED_PLATFORMS = ["gmail", "gdrive", "skyward", "classdojo", "brightwheel", "openai"]


class IntegrationConfigPayload(BaseModel):
    platform: str
    config: Dict[str, Any] = {}


@router.get("/status")
def integrations_status(current_user: User = Depends(get_current_user)) -> dict[str, object]:
    """Return integration status for the current user."""
    with db.session_scope() as session:
        user_integrations = (
            session.query(UserIntegration)
            .filter(UserIntegration.user_id == current_user.id)
            .all()
        )
        result = {}
        for ui in user_integrations:
            result[ui.platform] = {
                "status": ui.status,
                "last_synced": ui.last_synced.isoformat() if ui.last_synced else None,
                "config": ui.config(),
            }
        return {"ok": True, "integrations": result}


@router.post("/configure")
def configure_integration(
    payload: IntegrationConfigPayload,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Save or update integration configuration for the current user."""
    if payload.platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": f"Unsupported platform: {payload.platform}"},
        )

    with db.session_scope() as session:
        integration = (
            session.query(UserIntegration)
            .filter(UserIntegration.user_id == current_user.id, UserIntegration.platform == payload.platform)
            .first()
        )

        if integration:
            integration.config_json = json.dumps(payload.config)
            integration.status = "connected"
        else:
            integration = UserIntegration(
                user_id=current_user.id,
                platform=payload.platform,
                config_json=json.dumps(payload.config),
                status="connected",
            )
            session.add(integration)

        session.flush()
        return {"ok": True, "integration_id": integration.id}


@router.delete("/disconnect")
def disconnect_integration(
    platform: str,
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    """Remove an integration for the current user."""
    with db.session_scope() as session:
        integration = (
            session.query(UserIntegration)
            .filter(UserIntegration.user_id == current_user.id, UserIntegration.platform == platform)
            .first()
        )
        if integration:
            session.delete(integration)
        return {"ok": True}


@router.post("/gmail/token")
async def upload_gmail_token(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "invalid_file"})
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "empty_file"})
    save_token(data)
    return {"ok": True}
