"""User preferences routes."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from dependencies import get_current_user
from storage import get_db
from storage.models import User, UserPreference

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()


class PreferencesUpdate(BaseModel):
    digest_time: Optional[str] = None
    timezone: Optional[str] = None
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    urgent_alerts: Optional[bool] = None
    lookback_days: Optional[int] = None


@router.get("")
def get_preferences(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return user preferences (creates defaults if missing)."""
    with db.session_scope() as session:
        pref = session.query(UserPreference).filter(
            UserPreference.user_id == current_user.id
        ).first()
        if not pref:
            pref = UserPreference(user_id=current_user.id)
            session.add(pref)
            session.flush()

        return {
            "ok": True,
            "preferences": {
                "digest_time": pref.digest_time,
                "timezone": pref.timezone,
                "email_notifications": pref.email_notifications,
                "push_notifications": pref.push_notifications,
                "urgent_alerts": pref.urgent_alerts,
                "lookback_days": pref.lookback_days,
            },
        }


@router.put("")
def update_preferences(
    body: PreferencesUpdate,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Update user preferences."""
    with db.session_scope() as session:
        pref = session.query(UserPreference).filter(
            UserPreference.user_id == current_user.id
        ).first()
        if not pref:
            pref = UserPreference(user_id=current_user.id)
            session.add(pref)
            session.flush()

        if body.digest_time is not None:
            pref.digest_time = body.digest_time
        if body.timezone is not None:
            pref.timezone = body.timezone
        if body.email_notifications is not None:
            pref.email_notifications = body.email_notifications
        if body.push_notifications is not None:
            pref.push_notifications = body.push_notifications
        if body.urgent_alerts is not None:
            pref.urgent_alerts = body.urgent_alerts
        if body.lookback_days is not None:
            pref.lookback_days = body.lookback_days

    return {"ok": True}
