"""Integration management routes."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from config import get_settings
from dependencies import get_current_user
from services.integration_state import (
    DRIVE_SCOPE,
    GMAIL_SCOPE,
    drive_connector_ready,
    extract_oauth_payload,
    gmail_connector_ready,
    has_any_scope,
    oauth_has_access_token,
    oauth_has_refresh_token,
)
from services.gmail import save_token
from storage import get_db
from storage.models import User, UserIntegration

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()

SUPPORTED_PLATFORMS = ["gmail", "gdrive", "skyward", "classdojo", "brightwheel", "openai"]


class IntegrationConfigPayload(BaseModel):
    platform: str
    granted_scopes: Optional[str] = None
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
        logger.info(
            "Integrations status lookup: user_id=%s rows=%s providers=%s",
            current_user.id,
            len(user_integrations),
            [row.provider or row.platform for row in user_integrations],
        )
        result = {}
        for ui in user_integrations:
            key = ui.provider or ui.platform
            oauth_payload = extract_oauth_payload(ui)
            oauth_connected = bool(oauth_payload.get("access_token")) and has_any_scope(ui, (GMAIL_SCOPE, DRIVE_SCOPE))
            connector_ready = False
            needs_folder_id = False
            reauthorization_required = False
            effective_status = ui.status
            if key == "gmail":
                connector_ready = gmail_connector_ready(ui)
                has_scope = has_any_scope(ui, (GMAIL_SCOPE,))
                has_access = oauth_has_access_token(oauth_payload)
                has_refresh = oauth_has_refresh_token(oauth_payload)
                reauthorization_required = has_scope and has_access and not has_refresh
                if reauthorization_required:
                    effective_status = "reauthorization_required"
            elif key in ("google_drive", "gdrive"):
                connector_ready = drive_connector_ready(ui)
                cfg = ui.config()
                needs_folder_id = not bool((cfg.get("folder_id") or "").strip())
                has_scope = has_any_scope(ui, (DRIVE_SCOPE,))
                has_access = oauth_has_access_token(oauth_payload)
                has_refresh = oauth_has_refresh_token(oauth_payload)
                reauthorization_required = has_scope and has_access and not has_refresh
                if reauthorization_required:
                    effective_status = "reauthorization_required"
            else:
                connector_ready = ui.status == "connected"

            result[key] = {
                "status": effective_status,
                "last_synced": ui.last_synced.isoformat() if ui.last_synced else None,
                "granted_scopes": ui.granted_scopes,
                "config": ui.config(),
                "oauth_connected": oauth_connected,
                "connector_ready": connector_ready,
                "needs_folder_id": needs_folder_id,
                "reauthorization_required": reauthorization_required,
            }
            # Backward-compatible alias so frontend can safely read either key.
            if key == "google_drive":
                result["gdrive"] = result[key]
            logger.info(
                "Integration row status: user_id=%s key=%s db_status=%s effective_status=%s oauth_connected=%s connector_ready=%s has_access=%s has_refresh=%s scope=%s needs_folder_id=%s",
                current_user.id,
                key,
                ui.status,
                effective_status,
                oauth_connected,
                connector_ready,
                bool(oauth_payload.get("access_token")),
                bool(oauth_payload.get("refresh_token")),
                ui.granted_scopes or "",
                needs_folder_id,
            )
        logger.info("Integrations status response: user_id=%s payload=%s", current_user.id, result)
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
        provider = "google_drive" if payload.platform == "gdrive" else payload.platform
        integration = (
            session.query(UserIntegration)
            .filter(UserIntegration.user_id == current_user.id, UserIntegration.provider == provider)
            .first()
        )

        incoming_config = payload.config if isinstance(payload.config, dict) else {}
        if integration:
            integration.platform = payload.platform
            integration.provider = provider
            existing_config = integration.config()
            merged_config = {**existing_config, **incoming_config}
            integration.config_json = json.dumps(merged_config)
            oauth_payload = extract_oauth_payload(integration)
            if provider == "google_drive":
                has_scope = has_any_scope(integration, (DRIVE_SCOPE,))
                has_folder = bool((merged_config.get("folder_id") or "").strip())
                has_access = oauth_has_access_token(oauth_payload)
                has_refresh = oauth_has_refresh_token(oauth_payload)
                if has_scope and has_access and not has_refresh:
                    integration.status = "reauthorization_required"
                else:
                    integration.status = "connected" if has_scope and drive_connector_ready(integration) and has_folder else "scope_missing"
            elif provider == "gmail":
                has_scope = has_any_scope(integration, (GMAIL_SCOPE,))
                has_access = oauth_has_access_token(oauth_payload)
                has_refresh = oauth_has_refresh_token(oauth_payload)
                if has_scope and has_access and not has_refresh:
                    integration.status = "reauthorization_required"
                else:
                    integration.status = "connected" if has_scope and gmail_connector_ready(integration) else "scope_missing"
            else:
                integration.status = "connected"
            if payload.granted_scopes is not None:
                integration.granted_scopes = payload.granted_scopes
        else:
            status_value = "connected"
            if provider == "google_drive":
                has_folder = bool((incoming_config.get("folder_id") or "").strip())
                status_value = "connected" if has_folder else "scope_missing"
            integration = UserIntegration(
                user_id=current_user.id,
                platform=payload.platform,
                provider=provider,
                config_json=json.dumps(incoming_config),
                status=status_value,
                granted_scopes=payload.granted_scopes,
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
        provider = "google_drive" if platform == "gdrive" else platform
        integration = (
            session.query(UserIntegration)
            .filter(UserIntegration.user_id == current_user.id, UserIntegration.provider == provider)
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
    try:
        token_obj = json.loads(data.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "invalid_json"})
    with db.session_scope() as session:
        integration = (
            session.query(UserIntegration)
            .filter(
                UserIntegration.user_id == current_user.id,
                UserIntegration.provider == "gmail",
            )
            .first()
        )
        if integration:
            existing_cfg = integration.config()
            integration.credentials_json = json.dumps(token_obj)
            merged_cfg = {**existing_cfg, "token": token_obj, "oauth": token_obj}
            integration.config_json = json.dumps(merged_cfg)
            integration.granted_scopes = integration.granted_scopes or " ".join(token_obj.get("scopes", []))
            integration.status = "connected" if gmail_connector_ready(integration) else "scope_missing"
        else:
            session.add(
                UserIntegration(
                    user_id=current_user.id,
                    platform="gmail",
                    provider="gmail",
                    credentials_json=json.dumps(token_obj),
                    config_json=json.dumps({"token": token_obj, "oauth": token_obj}),
                    granted_scopes=" ".join(token_obj.get("scopes", [])),
                    status="connected",
                )
            )
    # Keep legacy file flow for local development compatibility.
    save_token(data)
    return {"ok": True}
