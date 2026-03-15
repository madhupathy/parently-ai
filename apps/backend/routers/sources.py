"""Sources router — school discovery + source management.

Endpoints:
  POST /sources/discover        — kick off school discovery for a child
  GET  /sources/discover/{id}   — poll discovery job status
  GET  /sources/{child_id}      — list school sources for a child
  POST /sources/{source_id}/confirm — user confirms a needs_confirmation source
  DELETE /sources/{source_id}   — remove a school source
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from dependencies import get_current_user
from storage import get_db
from storage.models import (
    Child,
    DiscoveryJob,
    SchoolSource,
    User,
    UserIntegration,
)

router = APIRouter()
logger = logging.getLogger(__name__)
db = get_db()


class DiscoverRequest(BaseModel):
    child_id: int
    school_query: str


class ConfirmRequest(BaseModel):
    pass  # empty body — just the POST action


class SuggestRequest(BaseModel):
    query: str
    limit: int = 6


# ---------------------------------------------------------------------------
# POST /sources/suggest
# ---------------------------------------------------------------------------

@router.post("/suggest")
def suggest_schools(
    payload: SuggestRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return school suggestions without persisting/linking any source."""
    query = (payload.query or "").strip()
    if len(query) < 3:
        return {"ok": True, "suggestions": []}

    from services.school_discovery_llm import discover_school_candidates

    candidates = discover_school_candidates(query)[: max(1, min(payload.limit, 10))]
    suggestions = []
    for c in candidates:
        homepage = c.get("homepage_url")
        suggestions.append(
            {
                "name": c.get("name"),
                "district_site_url": c.get("district_site_url"),
                "homepage_url": homepage,
                "calendar_page_url": c.get("calendar_page_url"),
                "school_domain": urlparse(homepage).netloc if homepage else None,
                "query_text": query,
            }
        )
    return {"ok": True, "suggestions": suggestions}


# ---------------------------------------------------------------------------
# POST /sources/discover
# ---------------------------------------------------------------------------

@router.post("/discover")
def discover_school(
    payload: DiscoverRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Start school discovery for a child. Runs synchronously for MVP."""
    # Validate child belongs to user
    with db.session_scope() as session:
        child = session.query(Child).filter(
            Child.id == payload.child_id,
            Child.user_id == current_user.id,
        ).first()
        if not child:
            raise HTTPException(status_code=404, detail="Child not found")

        # A new school selection should replace stale source links for this child.
        _clear_existing_sources_for_child(session, current_user.id, payload.child_id)

        # Create discovery job
        job = DiscoveryJob(
            user_id=current_user.id,
            child_id=payload.child_id,
            school_query_text=payload.school_query,
            status="running",
        )
        session.add(job)
        session.flush()
        job_id = job.id

    # Run discovery pipeline (sync for MVP)
    try:
        result = _run_discovery_pipeline(
            job_id=job_id,
            user_id=current_user.id,
            child_id=payload.child_id,
            school_query=payload.school_query,
        )
        return {"ok": True, "job_id": job_id, "status": "success", "result": result}
    except Exception as exc:
        logger.error("Discovery failed for job %d: %s", job_id, exc)
        with db.session_scope() as session:
            job = session.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
            if job:
                job.status = "failed"
                job.error_message = str(exc)[:1000]
                job.finished_at = datetime.utcnow()
        return {"ok": False, "job_id": job_id, "status": "failed", "error": str(exc)}


# ---------------------------------------------------------------------------
# GET /sources/discover/{job_id}
# ---------------------------------------------------------------------------

@router.get("/discover/{job_id}")
def get_discovery_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Poll discovery job status and results."""
    with db.session_scope() as session:
        job = session.query(DiscoveryJob).filter(
            DiscoveryJob.id == job_id,
            DiscoveryJob.user_id == current_user.id,
        ).first()
        if not job:
            raise HTTPException(status_code=404, detail="Discovery job not found")
        return {
            "ok": True,
            "job": {
                "id": job.id,
                "child_id": job.child_id,
                "school_query_text": job.school_query_text,
                "status": job.status,
                "result": job.result(),
                "error_message": job.error_message,
                "created_at": job.created_at.isoformat() if job.created_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            },
        }


# ---------------------------------------------------------------------------
# GET /sources/{child_id}
# ---------------------------------------------------------------------------

@router.get("/{child_id}")
def list_sources(
    child_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """List school sources for a child."""
    with db.session_scope() as session:
        child = session.query(Child).filter(
            Child.id == child_id,
            Child.user_id == current_user.id,
        ).first()
        if not child:
            raise HTTPException(status_code=404, detail="Child not found")

        sources = session.query(SchoolSource).filter(
            SchoolSource.child_id == child_id,
        ).order_by(SchoolSource.confidence_score.desc()).all()

        return {
            "ok": True,
            "sources": [_serialize_source(s) for s in sources],
        }


# ---------------------------------------------------------------------------
# POST /sources/{source_id}/confirm
# ---------------------------------------------------------------------------

@router.post("/{source_id}/confirm")
def confirm_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """User confirms a needs_confirmation source as verified."""
    with db.session_scope() as session:
        source = session.query(SchoolSource).filter(
            SchoolSource.id == source_id,
            SchoolSource.user_id == current_user.id,
        ).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        source.status = "verified"
        source.confidence_score = 1.0  # user-confirmed = max confidence

        # Create user_integrations entries
        _ensure_integrations(session, source)

        return {"ok": True, "source": _serialize_source(source)}


# ---------------------------------------------------------------------------
# DELETE /sources/{source_id}
# ---------------------------------------------------------------------------

@router.delete("/{source_id}")
def delete_source(
    source_id: int,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """Remove a school source."""
    with db.session_scope() as session:
        source = session.query(SchoolSource).filter(
            SchoolSource.id == source_id,
            SchoolSource.user_id == current_user.id,
        ).first()
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")
        session.delete(source)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Pipeline orchestration
# ---------------------------------------------------------------------------

def _run_discovery_pipeline(
    job_id: int,
    user_id: int,
    child_id: int,
    school_query: str,
) -> Dict[str, Any]:
    """Run the full school discovery pipeline synchronously.

    Steps:
      1. Build search queries (school_discovery.build_search_queries)
      2. LLM discovery (school_discovery_llm.discover_school_candidates)
      3. Site fetcher (site_fetcher.fetch_all_candidates)
      4. Score & classify (source_verifier.score_and_classify)
      5. Persist results (SchoolSource + optional UserIntegration)
    """
    from services.school_discovery import build_search_queries
    from services.school_discovery_llm import discover_school_candidates
    from services.site_fetcher import fetch_all_candidates
    from services.source_verifier import score_and_classify

    # Step 1–2: Generate candidates
    candidates = discover_school_candidates(school_query)

    if not candidates:
        _finish_job(job_id, "success", {"candidates": [], "sources_created": 0})
        return {"candidates": [], "sources_created": 0}

    # Step 3: Fetch site metadata
    fetch_results = fetch_all_candidates(candidates)

    # Step 4–5: Score, classify, persist
    sources_created = 0
    candidate_results = []

    for candidate, fetch_result in zip(candidates, fetch_results):
        score, classification = score_and_classify(
            candidate, fetch_result, school_query
        )

        candidate_detail = {
            "name": candidate.get("name"),
            "homepage_url": candidate.get("homepage_url"),
            "calendar_page_url": candidate.get("calendar_page_url"),
            "score": round(score, 3),
            "status": classification,
            "ics_links": fetch_result.get("found_ics_links", []),
            "rss_links": fetch_result.get("found_rss_links", []),
            "pdf_links": fetch_result.get("found_pdf_links", []),
        }
        candidate_results.append(candidate_detail)

        if classification in ("verified", "needs_confirmation"):
            source_id = _persist_source(
                user_id=user_id,
                child_id=child_id,
                school_query=school_query,
                candidate=candidate,
                fetch_result=fetch_result,
                score=score,
                status=classification,
            )
            candidate_detail["source_id"] = source_id
            sources_created += 1

    result = {
        "candidates": candidate_results,
        "sources_created": sources_created,
    }
    _finish_job(job_id, "success", result)

    # Auto-update child's school_name + school_domain from best verified source
    _update_child_from_best_source(child_id)

    return result


def _persist_source(
    user_id: int,
    child_id: int,
    school_query: str,
    candidate: Dict[str, Any],
    fetch_result: Dict[str, Any],
    score: float,
    status: str,
) -> int:
    """Create a SchoolSource row and optional UserIntegration entries."""
    with db.session_scope() as session:
        source = SchoolSource(
            user_id=user_id,
            child_id=child_id,
            school_query=school_query,
            verified_name=candidate.get("name"),
            homepage_url=candidate.get("homepage_url"),
            district_url=candidate.get("district_site_url"),
            calendar_page_url=candidate.get("calendar_page_url"),
            ics_urls_json=json.dumps(fetch_result.get("found_ics_links", [])),
            rss_urls_json=json.dumps(fetch_result.get("found_rss_links", [])),
            pdf_urls_json=json.dumps(fetch_result.get("found_pdf_links", [])),
            confidence_score=score,
            status=status,
        )
        session.add(source)
        session.flush()
        source_id = source.id

        # Create/update child-specific public source integration state.
        if status in ("verified", "needs_confirmation"):
            _ensure_integrations(session, source)

    return source_id


def _ensure_integrations(session: Any, source: SchoolSource) -> None:
    """Upsert public source integrations for a specific child/source."""
    for platform in ("public_calendar", "public_website"):
        all_for_platform = session.query(UserIntegration).filter(
            UserIntegration.user_id == source.user_id,
            UserIntegration.platform == platform,
        ).all()
        existing = None
        for row in all_for_platform:
            cfg = row.config()
            if cfg.get("child_id") == source.child_id:
                existing = row
                break

        integration_status = "connected" if source.status == "verified" else "pending_confirmation"
        integration_config = {
            "school_source_id": source.id,
            "child_id": source.child_id,
            "homepage_url": source.homepage_url,
            "calendar_page_url": source.calendar_page_url,
            "status": source.status,
        }
        if not existing:
            session.add(UserIntegration(
                user_id=source.user_id,
                platform=platform,
                status=integration_status,
                config_json=json.dumps(integration_config),
            ))
        else:
            existing.status = integration_status
            existing.config_json = json.dumps(integration_config)


def _update_child_from_best_source(child_id: int) -> None:
    """Auto-populate child.school_name and school_domain from the top verified source."""
    with db.session_scope() as session:
        best = session.query(SchoolSource).filter(
            SchoolSource.child_id == child_id,
            SchoolSource.status == "verified",
        ).order_by(SchoolSource.confidence_score.desc()).first()

        if not best:
            return

        child = session.query(Child).filter(Child.id == child_id).first()
        if not child:
            return

        if best.verified_name and not child.school_name:
            child.school_name = best.verified_name
        if best.homepage_url and not child.school_domain:
            domain = urlparse(best.homepage_url).netloc
            if domain:
                child.school_domain = domain


def _clear_existing_sources_for_child(session: Any, user_id: int, child_id: int) -> None:
    """Remove stale school source links/integrations before re-discovery for this child."""
    existing_sources = session.query(SchoolSource).filter(
        SchoolSource.user_id == user_id,
        SchoolSource.child_id == child_id,
    ).all()
    source_ids = {s.id for s in existing_sources}
    for source in existing_sources:
        session.delete(source)

    integrations = session.query(UserIntegration).filter(
        UserIntegration.user_id == user_id,
        UserIntegration.platform.in_(("public_calendar", "public_website")),
    ).all()
    for integration in integrations:
        cfg = integration.config()
        if cfg.get("child_id") == child_id or cfg.get("school_source_id") in source_ids:
            session.delete(integration)


def _finish_job(job_id: int, status: str, result: Dict[str, Any]) -> None:
    """Update a DiscoveryJob with final status and result."""
    with db.session_scope() as session:
        job = session.query(DiscoveryJob).filter(DiscoveryJob.id == job_id).first()
        if job:
            job.status = status
            job.result_json = json.dumps(result, default=str)
            job.finished_at = datetime.utcnow()


def _serialize_source(source: SchoolSource) -> Dict[str, Any]:
    if source.status == "verified":
        state = "linked"
    elif source.status == "needs_confirmation":
        state = "discovered_needs_confirmation"
    else:
        state = "failed"

    return {
        "id": source.id,
        "child_id": source.child_id,
        "school_query": source.school_query,
        "verified_name": source.verified_name,
        "homepage_url": source.homepage_url,
        "district_url": source.district_url,
        "calendar_page_url": source.calendar_page_url,
        "ics_urls": source.ics_urls(),
        "rss_urls": source.rss_urls(),
        "pdf_urls": source.pdf_urls(),
        "confidence_score": source.confidence_score,
        "status": source.status,
        "state": state,
        "created_at": source.created_at.isoformat() if source.created_at else None,
        "last_ingested_at": source.last_ingested_at.isoformat() if source.last_ingested_at else None,
    }
