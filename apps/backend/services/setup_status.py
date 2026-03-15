"""Centralized setup readiness calculation."""

from __future__ import annotations

from typing import Any, Dict

from services.integration_state import drive_connector_ready, gmail_connector_ready
from storage import get_db
from storage.models import Child, SchoolSource, UserIntegration


def compute_setup_status(user_id: int) -> Dict[str, Any]:
    """Return canonical setup status used by onboarding and digest readiness."""
    db = get_db()
    with db.session_scope() as session:
        children = session.query(Child).filter(Child.user_id == user_id).all()
        child_ids = [child.id for child in children]
        has_children = len(child_ids) > 0
        has_school = any((child.school_name or "").strip() for child in children)

        sources = []
        if child_ids:
            sources = session.query(SchoolSource).filter(
                SchoolSource.child_id.in_(child_ids)
            ).all()
        has_sources = any(source.status in ("linked", "verified") for source in sources)

        integrations = session.query(UserIntegration).filter(
            UserIntegration.user_id == user_id
        ).all()
        by_provider = {row.provider or row.platform: row for row in integrations}
        gmail_row = by_provider.get("gmail")
        drive_row = by_provider.get("google_drive") or by_provider.get("gdrive")

        gmail_connected = bool(gmail_row and gmail_connector_ready(gmail_row))
        drive_connected = bool(drive_row and drive_connector_ready(drive_row))

    return {
        "has_children": has_children,
        "has_school": has_school,
        "has_sources": has_sources,
        "gmail_connected": gmail_connected,
        "drive_connected": drive_connected,
        "digest_ready": has_children and has_sources,
    }
