"""Digest-related API routes.

Key behaviors:
  - One digest per day (upsert: re-run same day updates the record)
  - Auto-create notifications on new/regenerated digests
  - Dashboard endpoint: today's digest + unread count + past N days
  - History endpoint with free (7 days) vs premium (unlimited) gating
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from agents.graph import run_digest
from dependencies import get_current_user, check_digest_entitlement
from storage import get_db
from storage.models import (
    Digest, DigestJob, LLMUsage, Notification, User, UserEntitlement,
)

router = APIRouter()
logger = logging.getLogger(__name__)

db = get_db()


def _serialize_digest(d: Digest) -> Dict[str, Any]:
    return {
        "id": d.id,
        "child_id": d.child_id,
        "digest_date": d.digest_date,
        "created_at": d.created_at.isoformat(),
        "summary_md": d.summary_md,
        "items": d.items(),
        "source": d.source,
    }


def _serialize_digest_summary(d: Digest) -> Dict[str, Any]:
    """Lightweight summary for history lists (no full markdown)."""
    items = d.items()
    return {
        "id": d.id,
        "child_id": d.child_id,
        "digest_date": d.digest_date,
        "created_at": d.created_at.isoformat(),
        "item_count": len(items),
        "source": d.source,
        "preview": d.summary_md[:200] if d.summary_md else "",
    }


# ── Dashboard ─────────────────────────────────────

@router.get("/dashboard")
def dashboard(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Dashboard data: today's digest + unread count + past 7 days."""
    today_str = date.today().isoformat()
    seven_days_ago = date.today() - timedelta(days=7)

    with db.session_scope() as session:
        # Today's digest
        today_digest_row = (
            session.query(Digest)
            .filter(Digest.user_id == current_user.id, Digest.digest_date == today_str)
            .order_by(Digest.created_at.desc())
            .first()
        )
        today_digest = _serialize_digest(today_digest_row) if today_digest_row else None

        # Past 7 days (excluding today)
        past_digests_rows = (
            session.query(Digest)
            .filter(
                Digest.user_id == current_user.id,
                Digest.digest_date != None,
                Digest.digest_date < today_str,
                Digest.digest_date >= seven_days_ago.isoformat(),
            )
            .order_by(Digest.digest_date.desc())
            .all()
        )
        past_digests = [_serialize_digest_summary(d) for d in past_digests_rows]

        # Unread notification count
        unread_count = session.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        ).count()

    return {
        "ok": True,
        "today_digest": today_digest,
        "past_digests": past_digests,
        "unread_count": unread_count,
    }


# ── Run Digest (idempotent upsert) ───────────────

@router.post("/run")
def run_digest_endpoint(
    current_user: User = Depends(check_digest_entitlement),
    refresh: bool = Query(False),
) -> Dict[str, Any]:
    """Trigger digest workflow. One digest per day — re-run updates the same record."""
    today_str = date.today().isoformat()

    # Return cached same-day digest unless refresh=True
    if not refresh:
        with db.session_scope() as session:
            existing = (
                session.query(Digest)
                .filter(Digest.user_id == current_user.id, Digest.digest_date == today_str)
                .first()
            )
            if existing:
                return {
                    "ok": True,
                    "id": existing.id,
                    "cached": True,
                    "digest": _serialize_digest(existing),
                }

    # Create a DigestJob
    with db.session_scope() as session:
        job = DigestJob(user_id=current_user.id, status="running", started_at=datetime.utcnow())
        session.add(job)
        session.flush()
        job_id = job.id

    try:
        payload = {"email": current_user.email, "user_id": current_user.id}
        result = run_digest(payload)

        with db.session_scope() as session:
            # Upsert: find existing same-day digest or create new
            existing = (
                session.query(Digest)
                .filter(Digest.user_id == current_user.id, Digest.digest_date == today_str)
                .first()
            )

            is_new = existing is None
            if existing:
                # Update existing record
                existing.source = result.get("source", "gmail")
                existing.summary_md = result.get("digest_markdown", "")
                existing.items_json = result.get("items_json", "[]")
                existing.raw_json = result.get("raw_json", "{}")
                existing.created_at = datetime.utcnow()
                digest_id = existing.id
            else:
                # Create new digest
                digest_obj = Digest(
                    user_id=current_user.id,
                    digest_date=today_str,
                    source=result.get("source", "gmail"),
                    summary_md=result.get("digest_markdown", ""),
                    items_json=result.get("items_json", "[]"),
                    raw_json=result.get("raw_json", "{}"),
                )
                session.add(digest_obj)
                session.flush()
                digest_id = digest_obj.id

            # Record LLM usage
            usage = result.get("llm_usage")
            if usage:
                session.add(LLMUsage(
                    user_id=current_user.id,
                    digest_id=digest_id,
                    model=usage.get("model", "unknown"),
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    estimated_cost_usd=usage.get("estimated_cost_usd", 0.0),
                ))

            # Decrement free plan digests only on first run of the day
            if is_new:
                entitlement = session.query(UserEntitlement).filter(
                    UserEntitlement.user_id == current_user.id
                ).first()
                if entitlement and not entitlement.premium_active and entitlement.digests_remaining > 0:
                    entitlement.digests_remaining -= 1

            # Create notification
            _create_digest_notification(session, current_user.id, digest_id, is_new)

            # Update job
            job_row = session.query(DigestJob).filter(DigestJob.id == job_id).first()
            if job_row:
                job_row.status = "success"
                job_row.finished_at = datetime.utcnow()
                job_row.digest_id = digest_id

        return {"ok": True, "id": digest_id, "cached": False}
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to run digest: %s", exc)
        with db.session_scope() as session:
            job_row = session.query(DigestJob).filter(DigestJob.id == job_id).first()
            if job_row:
                job_row.status = "failed"
                job_row.finished_at = datetime.utcnow()
                job_row.error_message = str(exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": "digest_failed", "message": str(exc)},
        ) from exc


# ── Latest (backward compat) ─────────────────────

@router.get("/latest")
def latest_digest(current_user: User = Depends(get_current_user)) -> Dict[str, Any]:
    """Return the most recent digest for the current user."""
    with db.session_scope() as session:
        digest = (
            session.query(Digest)
            .filter(Digest.user_id == current_user.id)
            .order_by(Digest.created_at.desc())
            .first()
        )
        if not digest:
            return {"ok": True, "digest": None}
        return {"ok": True, "digest": _serialize_digest(digest)}


# ── History ───────────────────────────────────────

@router.get("/history")
def digest_history(
    current_user: User = Depends(get_current_user),
    days: int = Query(7, ge=1, le=365),
) -> Dict[str, Any]:
    """Return digest history. Free = 7 days max, Premium = up to 365."""
    with db.session_scope() as session:
        # Check premium status
        ent = session.query(UserEntitlement).filter(
            UserEntitlement.user_id == current_user.id
        ).first()
        is_premium = ent.premium_active if ent else False

        max_days = 365 if is_premium else 7
        effective_days = min(days, max_days)
        cutoff = date.today() - timedelta(days=effective_days)

        digests = (
            session.query(Digest)
            .filter(
                Digest.user_id == current_user.id,
                Digest.digest_date != None,
                Digest.digest_date >= cutoff.isoformat(),
            )
            .order_by(Digest.digest_date.desc())
            .all()
        )

        return {
            "ok": True,
            "digests": [_serialize_digest_summary(d) for d in digests],
            "is_premium": is_premium,
            "max_days": max_days,
            "effective_days": effective_days,
        }


# ── Single digest by ID ──────────────────────────

@router.get("/{digest_id}")
def get_digest(
    digest_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return a single digest by ID. Also marks related notifications as read."""
    with db.session_scope() as session:
        digest = session.query(Digest).filter(
            Digest.id == digest_id,
            Digest.user_id == current_user.id,
        ).first()
        if not digest:
            raise HTTPException(status_code=404, detail="Digest not found")

        # Mark related notifications as read
        unread_notifs = session.query(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.digest_id == digest_id,
            Notification.is_read == False,
        ).all()
        now = datetime.utcnow()
        for n in unread_notifs:
            n.is_read = True
            n.read_at = now

        return {"ok": True, "digest": _serialize_digest(digest)}


# ── Helpers ───────────────────────────────────────

def _create_digest_notification(
    session: Any,
    user_id: int,
    digest_id: int,
    is_new: bool,
) -> None:
    """Create a DIGEST_READY notification. Only for new digests or significant regenerations."""
    title = "Your daily digest is ready" if is_new else "Your digest has been updated"
    notif = Notification(
        user_id=user_id,
        digest_id=digest_id,
        type="DIGEST_READY",
        title=title,
        body="Tap to view your calm school overview for today.",
    )
    session.add(notif)
