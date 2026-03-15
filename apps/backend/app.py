"""FastAPI application entrypoint for Parently."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from dependencies import verify_cron_secret
from routers import auth, billing, children, contact, digest, integrations, notifications, preferences, search_profiles, setup, sources, uploads
from storage import get_db
from storage.models import User, UserEntitlement

logger = logging.getLogger(__name__)

settings = get_settings()
get_db()  # ensure tables created

app = FastAPI(title="Parently", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/healthz")
@app.get("/health")
def health() -> Dict[str, bool]:
    """Simple health probes used by Railway."""

    return {"ok": True}


@app.post("/api/internal/run-daily-digests", dependencies=[Depends(verify_cron_secret)])
def run_daily_digests() -> Dict[str, Any]:
    """Cron endpoint: generate digests for all active users (one per day, upsert)."""
    from datetime import date
    from agents.graph import run_digest
    from storage.models import Digest, DigestJob, LLMUsage, Notification

    db = get_db()
    results: List[Dict[str, Any]] = []
    today_str = date.today().isoformat()

    with db.session_scope() as session:
        users = session.query(User).all()
        user_list = [(u.id, u.email) for u in users]

    for user_id, email in user_list:
        try:
            # Check entitlement
            with db.session_scope() as session:
                ent = session.query(UserEntitlement).filter(
                    UserEntitlement.user_id == user_id
                ).first()
                if ent and not ent.premium_active and ent.digests_remaining <= 0:
                    results.append({"user_id": user_id, "status": "skipped", "reason": "no_digests_remaining"})
                    continue

            # Skip if already ran today
            with db.session_scope() as session:
                existing = session.query(Digest).filter(
                    Digest.user_id == user_id,
                    Digest.digest_date == today_str,
                ).first()
                if existing:
                    results.append({"user_id": user_id, "status": "skipped", "reason": "already_ran_today"})
                    continue

            payload = {"email": email, "user_id": user_id}
            result = run_digest(payload)

            with db.session_scope() as session:
                digest_obj = Digest(
                    user_id=user_id,
                    digest_date=today_str,
                    source=result.get("source", "cron"),
                    summary_md=result.get("digest_markdown", ""),
                    items_json=result.get("items_json", "[]"),
                    raw_json=result.get("raw_json", "{}"),
                )
                session.add(digest_obj)
                session.flush()

                usage = result.get("llm_usage")
                if usage:
                    session.add(LLMUsage(
                        user_id=user_id,
                        digest_id=digest_obj.id,
                        model=usage.get("model", "unknown"),
                        prompt_tokens=usage.get("prompt_tokens", 0),
                        completion_tokens=usage.get("completion_tokens", 0),
                        estimated_cost_usd=usage.get("estimated_cost_usd", 0.0),
                    ))

                ent = session.query(UserEntitlement).filter(
                    UserEntitlement.user_id == user_id
                ).first()
                if ent and not ent.premium_active and ent.digests_remaining > 0:
                    ent.digests_remaining -= 1

                # Create notification
                session.add(Notification(
                    user_id=user_id,
                    digest_id=digest_obj.id,
                    type="DIGEST_READY",
                    title="Your daily digest is ready",
                    body="Tap to view your calm school overview for today.",
                ))

            results.append({"user_id": user_id, "status": "success"})
        except Exception as exc:
            logger.error("Cron digest failed for user %d: %s", user_id, exc)
            results.append({"user_id": user_id, "status": "failed", "error": str(exc)})

    return {"ok": True, "results": results}


@app.post("/api/internal/refresh-school-sources", dependencies=[Depends(verify_cron_secret)])
def refresh_school_sources() -> Dict[str, Any]:
    """Cron endpoint: re-ingest all verified school sources daily."""
    from storage.models import SchoolSource
    from services.calendar_ingest import ingest_school_source
    from services.website_ingest import ingest_school_website

    db = get_db()
    results: List[Dict[str, Any]] = []

    with db.session_scope() as session:
        sources = session.query(SchoolSource).filter(
            SchoolSource.status.in_(("linked", "verified"))
        ).all()
        source_data = [
            {
                "id": s.id,
                "user_id": s.user_id,
                "child_id": s.child_id,
                "verified_name": s.verified_name or "School",
                "homepage_url": s.homepage_url,
                "calendar_page_url": s.calendar_page_url,
                "ics_urls": s.ics_urls(),
                "rss_urls": s.rss_urls(),
                "pdf_urls": s.pdf_urls(),
            }
            for s in sources
        ]

    for sd in source_data:
        try:
            cal_result = ingest_school_source(
                school_source_id=sd["id"],
                child_id=sd["child_id"],
                calendar_page_url=sd["calendar_page_url"],
                ics_urls=sd["ics_urls"],
                rss_urls=sd["rss_urls"],
                pdf_urls=sd["pdf_urls"],
                school_name=sd["verified_name"],
            )
            web_result = ingest_school_website(
                school_source_id=sd["id"],
                child_id=sd["child_id"],
                homepage_url=sd["homepage_url"],
                school_name=sd["verified_name"],
            )
            # Update last_ingested_at
            with db.session_scope() as session:
                src = session.query(SchoolSource).filter(SchoolSource.id == sd["id"]).first()
                if src:
                    src.last_ingested_at = datetime.utcnow()

            results.append({
                "source_id": sd["id"],
                "status": "success",
                "calendar": cal_result,
                "website": web_result,
            })
        except Exception as exc:
            logger.error("Refresh failed for source %d: %s", sd["id"], exc)
            results.append({"source_id": sd["id"], "status": "failed", "error": str(exc)})

    return {"ok": True, "refreshed": len(results), "results": results}


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(contact.router, prefix="/api/contact", tags=["contact"])
app.include_router(digest.router, prefix="/api/digest", tags=["digest"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(children.router, prefix="/api/children", tags=["children"])
app.include_router(preferences.router, prefix="/api/preferences", tags=["preferences"])
app.include_router(search_profiles.router, prefix="/api/search-profiles", tags=["search-profiles"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])
app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
app.include_router(setup.router, prefix="/api/setup", tags=["setup"])
