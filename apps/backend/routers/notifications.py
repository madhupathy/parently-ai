"""Notification CRUD routes."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from dependencies import get_current_user
from storage import get_db
from storage.models import Notification, User

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()


def _serialize(n: Notification) -> Dict[str, Any]:
    return {
        "id": n.id,
        "digest_id": n.digest_id,
        "type": n.type,
        "title": n.title,
        "body": n.body,
        "is_read": n.is_read,
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "created_at": n.created_at.isoformat(),
    }


@router.get("")
def list_notifications(
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    unread_only: bool = Query(False),
) -> Dict[str, Any]:
    """List notifications for the current user (newest first)."""
    with db.session_scope() as session:
        q = session.query(Notification).filter(
            Notification.user_id == current_user.id
        )
        if unread_only:
            q = q.filter(Notification.is_read == False)
        notifications = q.order_by(Notification.created_at.desc()).limit(limit).all()

        unread_count = session.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        ).count()

        return {
            "ok": True,
            "notifications": [_serialize(n) for n in notifications],
            "unread_count": unread_count,
        }


@router.get("/unread-count")
def unread_count(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return just the unread notification count (lightweight poll)."""
    with db.session_scope() as session:
        count = session.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        ).count()
    return {"ok": True, "unread_count": count}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mark a single notification as read."""
    with db.session_scope() as session:
        notif = session.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        ).first()
        if not notif:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
        if not notif.is_read:
            notif.is_read = True
            notif.read_at = datetime.utcnow()
    return {"ok": True}


@router.post("/mark-all-read")
def mark_all_read(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Mark all notifications as read for the current user."""
    with db.session_scope() as session:
        now = datetime.utcnow()
        unread = session.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        ).all()
        count = 0
        for n in unread:
            n.is_read = True
            n.read_at = now
            count += 1
    logger.info("Marked %d notifications as read for user %d", count, current_user.id)
    return {"ok": True, "marked": count}
