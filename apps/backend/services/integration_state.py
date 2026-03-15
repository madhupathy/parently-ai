"""Helpers for OAuth-backed integration readiness and credential extraction."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Optional, Set

from storage.models import UserIntegration

GMAIL_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.readonly"

_REQUIRED_OAUTH_FIELDS = (
    "access_token",
    "refresh_token",
    "token_uri",
    "client_id",
    "client_secret",
)


def parse_scopes(scopes: Optional[str]) -> Set[str]:
    raw = (scopes or "").strip()
    if not raw:
        return set()
    # Google returns space-delimited scopes in OAuth responses.
    return {part.strip() for part in raw.split(" ") if part.strip()}


def _safe_json(value: Optional[str]) -> Dict[str, Any]:
    if not value:
        return {}
    try:
        decoded = json.loads(value)
        return decoded if isinstance(decoded, dict) else {}
    except Exception:
        return {}


def extract_oauth_payload(integration: UserIntegration) -> Dict[str, Any]:
    """Merge token payload from credentials_json and config_json."""
    payload: Dict[str, Any] = {}
    creds = _safe_json(integration.credentials_json)
    cfg = _safe_json(integration.config_json)

    if isinstance(creds, dict):
        payload.update(creds)
    token_cfg = cfg.get("token")
    if isinstance(token_cfg, dict):
        payload.update(token_cfg)
    oauth_cfg = cfg.get("oauth")
    if isinstance(oauth_cfg, dict):
        payload.update(oauth_cfg)

    # Normalize "token" alias used by some Google auth formats.
    if payload.get("token") and not payload.get("access_token"):
        payload["access_token"] = payload.get("token")
    if payload.get("access_token") and not payload.get("token"):
        payload["token"] = payload.get("access_token")
    return payload


def oauth_credentials_complete(payload: Dict[str, Any]) -> bool:
    return all(bool(payload.get(field)) for field in _REQUIRED_OAUTH_FIELDS)


def has_any_scope(integration: UserIntegration, required_scopes: Iterable[str]) -> bool:
    scopes = parse_scopes(integration.granted_scopes)
    return any(scope in scopes for scope in required_scopes)


def gmail_connector_ready(integration: UserIntegration) -> bool:
    payload = extract_oauth_payload(integration)
    return oauth_credentials_complete(payload) and has_any_scope(integration, (GMAIL_SCOPE,))


def drive_connector_ready(integration: UserIntegration) -> bool:
    payload = extract_oauth_payload(integration)
    cfg = _safe_json(integration.config_json)
    has_folder = bool((cfg.get("folder_id") or "").strip()) if isinstance(cfg, dict) else False
    return oauth_credentials_complete(payload) and has_any_scope(integration, (DRIVE_SCOPE,)) and has_folder
