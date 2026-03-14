"""Calendar ingestion — ICS, RSS, HTML, and PDF calendar sources → Documents.

Handles multiple calendar formats:
  - ICS (iCalendar) files → parse with icalendar library
  - RSS/Atom feeds → parse with feedparser
  - HTML calendar pages → extract with LLM prompt
  - PDF calendars → extract text with pypdf, then LLM

All normalized events are stored as Documents with source_type metadata
and ingested into the RAG store for retrieval.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional

import httpx

from storage import get_db, rag_store
from storage.models import Document

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_USER_AGENT = "Parently-SchoolBot/1.0 (+https://parently.app)"


def ingest_school_source(
    school_source_id: int,
    child_id: int,
    calendar_page_url: Optional[str] = None,
    ics_urls: Optional[List[str]] = None,
    rss_urls: Optional[List[str]] = None,
    pdf_urls: Optional[List[str]] = None,
    school_name: str = "School",
) -> Dict[str, Any]:
    """Ingest all calendar assets for a school source.

    Returns summary of what was ingested.
    """
    results = {
        "ics_events": 0,
        "rss_events": 0,
        "html_events": 0,
        "pdf_docs": 0,
        "documents_created": 0,
    }

    # ICS feeds
    for url in (ics_urls or []):
        try:
            events = parse_ics_from_url(url)
            if events:
                doc_id = _store_events_as_document(
                    events, school_name, "web_calendar_ics", url, child_id
                )
                results["ics_events"] += len(events)
                results["documents_created"] += 1
        except Exception as exc:
            logger.warning("ICS ingest failed for %s: %s", url, exc)

    # RSS/Atom feeds
    for url in (rss_urls or []):
        try:
            events = parse_rss_from_url(url)
            if events:
                doc_id = _store_events_as_document(
                    events, school_name, "web_calendar_rss", url, child_id
                )
                results["rss_events"] += len(events)
                results["documents_created"] += 1
        except Exception as exc:
            logger.warning("RSS ingest failed for %s: %s", url, exc)

    # HTML calendar page
    if calendar_page_url:
        try:
            events = extract_html_calendar(calendar_page_url, school_name)
            if events:
                doc_id = _store_events_as_document(
                    events, school_name, "web_calendar_html", calendar_page_url, child_id
                )
                results["html_events"] += len(events)
                results["documents_created"] += 1
        except Exception as exc:
            logger.warning("HTML calendar ingest failed for %s: %s", calendar_page_url, exc)

    # PDF calendars
    for url in (pdf_urls or []):
        try:
            text = _fetch_pdf_text(url)
            if text:
                doc_id = _store_pdf_document(text, school_name, url, child_id)
                results["pdf_docs"] += 1
                results["documents_created"] += 1
        except Exception as exc:
            logger.warning("PDF ingest failed for %s: %s", url, exc)

    logger.info(
        "Calendar ingest for source %d: %s",
        school_source_id, results,
    )
    return results


# ---------------------------------------------------------------------------
# ICS parsing
# ---------------------------------------------------------------------------

def parse_ics_from_url(url: str) -> List[Dict[str, Any]]:
    """Fetch and parse an ICS file into normalized events."""
    content = _fetch_text(url)
    if not content:
        return []
    return parse_ics_text(content)


def parse_ics_text(text: str) -> List[Dict[str, Any]]:
    """Parse ICS text content into a list of event dicts."""
    from icalendar import Calendar

    events = []
    try:
        cal = Calendar.from_ical(text)
    except Exception as exc:
        logger.warning("Failed to parse ICS: %s", exc)
        return []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        dtstart = component.get("dtstart")
        dtend = component.get("dtend")
        summary = str(component.get("summary", ""))
        description = str(component.get("description", ""))
        location = str(component.get("location", ""))

        start_str = _dt_to_iso(dtstart.dt) if dtstart else None
        end_str = _dt_to_iso(dtend.dt) if dtend else None

        if not summary and not description:
            continue

        events.append({
            "title": summary,
            "start_date": start_str,
            "end_date": end_str,
            "all_day": isinstance(dtstart.dt, date) and not isinstance(dtstart.dt, datetime) if dtstart else True,
            "description": description[:500],
            "location": location[:200],
            "category": _categorize_event(summary + " " + description),
            "source_type": "ics",
        })

    return events


# ---------------------------------------------------------------------------
# RSS/Atom parsing
# ---------------------------------------------------------------------------

def parse_rss_from_url(url: str) -> List[Dict[str, Any]]:
    """Fetch and parse an RSS/Atom feed into normalized events."""
    import feedparser

    content = _fetch_text(url)
    if not content:
        return []

    feed = feedparser.parse(content)
    events = []

    for entry in feed.entries:
        title = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        published = entry.get("published", "")
        link = entry.get("link", "")

        # Try to parse date
        date_str = None
        if published:
            try:
                from dateutil import parser as date_parser
                parsed_dt = date_parser.parse(published)
                date_str = parsed_dt.date().isoformat()
            except (ValueError, OverflowError):
                pass

        if not title:
            continue

        events.append({
            "title": title,
            "start_date": date_str,
            "end_date": None,
            "all_day": True,
            "description": _strip_html(summary)[:500],
            "category": _categorize_event(title + " " + summary),
            "source_type": "rss",
            "source_url": link,
        })

    return events


# ---------------------------------------------------------------------------
# HTML calendar extraction (LLM-assisted)
# ---------------------------------------------------------------------------

def extract_html_calendar(
    url: str,
    school_name: str,
) -> List[Dict[str, Any]]:
    """Fetch an HTML calendar page and extract events using LLM."""
    from bs4 import BeautifulSoup
    from services.gemini import generate
    from services.prompt_loader import load_prompt

    html = _fetch_text(url)
    if not html:
        return []

    # Strip nav/footer to reduce token usage
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["nav", "footer", "header", "script", "style"]):
        tag.decompose()
    clean_text = soup.get_text(separator="\n", strip=True)[:8000]

    system_prompt = load_prompt("calendar_extract_prompt_v1")
    user_prompt = json.dumps({
        "school_name": school_name,
        "page_url": url,
        "raw_content": clean_text,
    })

    result = generate(prompt=user_prompt, system_instruction=system_prompt)
    if not result.text:
        return []

    return _parse_llm_events(result.text)


# ---------------------------------------------------------------------------
# PDF calendar
# ---------------------------------------------------------------------------

def _fetch_pdf_text(url: str) -> Optional[str]:
    """Download a PDF and extract text."""
    try:
        with httpx.Client(timeout=_TIMEOUT, headers={"User-Agent": _USER_AGENT}) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None

        import io
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(resp.content))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except Exception as exc:
        logger.warning("PDF fetch/parse failed for %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _store_events_as_document(
    events: List[Dict[str, Any]],
    school_name: str,
    source_type: str,
    source_url: str,
    child_id: int,
) -> int:
    """Store calendar events as a Document in the RAG store."""
    # Build a human-readable text representation for embedding
    text_parts = [f"# Calendar Events — {school_name}\n"]
    for ev in events:
        line = f"- {ev.get('title', 'Event')}"
        if ev.get("start_date"):
            line += f" ({ev['start_date']})"
        if ev.get("description"):
            line += f": {ev['description'][:200]}"
        text_parts.append(line)

    text = "\n".join(text_parts)

    # Use a content-based filename for dedup
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
    filename = f"calendar_{source_type}_{content_hash}.md"

    # Check for existing document with same filename (dedup)
    db = get_db()
    with db.session_scope() as session:
        existing = session.query(Document).filter(
            Document.filename == filename
        ).first()
        if existing:
            # Update existing document
            existing.text = text
            existing.metadata_json = json.dumps({
                "source_type": source_type,
                "source_url": source_url,
                "child_id": child_id,
                "school_name": school_name,
                "event_count": len(events),
                "events": events,
                "updated_at": datetime.utcnow().isoformat(),
            })
            return existing.id

    # Create new document via rag_store (handles chunking + embedding)
    doc_id = rag_store.add_document(filename, "text/markdown", text)

    # Update metadata on the document
    with db.session_scope() as session:
        doc = session.query(Document).filter(Document.id == doc_id).first()
        if doc and hasattr(doc, "metadata_json"):
            doc.metadata_json = json.dumps({
                "source_type": source_type,
                "source_url": source_url,
                "child_id": child_id,
                "school_name": school_name,
                "event_count": len(events),
                "events": events,
            })

    return doc_id


def _store_pdf_document(
    text: str,
    school_name: str,
    source_url: str,
    child_id: int,
) -> int:
    """Store a PDF's extracted text as a Document."""
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
    filename = f"calendar_pdf_{content_hash}.pdf"

    doc_id = rag_store.add_document(filename, "application/pdf", text)

    db = get_db()
    with db.session_scope() as session:
        doc = session.query(Document).filter(Document.id == doc_id).first()
        if doc and hasattr(doc, "metadata_json"):
            doc.metadata_json = json.dumps({
                "source_type": "web_calendar_pdf",
                "source_url": source_url,
                "child_id": child_id,
                "school_name": school_name,
            })

    return doc_id


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _fetch_text(url: str) -> Optional[str]:
    """Fetch URL content as text."""
    try:
        with httpx.Client(
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                return resp.text
    except Exception as exc:
        logger.debug("Failed to fetch %s: %s", url, exc)
    return None


def _dt_to_iso(dt: Any) -> Optional[str]:
    """Convert a datetime or date to ISO string."""
    if isinstance(dt, datetime):
        return dt.date().isoformat()
    if isinstance(dt, date):
        return dt.isoformat()
    return str(dt) if dt else None


def _categorize_event(text: str) -> str:
    """Simple keyword-based event categorization."""
    lower = text.lower()
    if any(w in lower for w in ("holiday", "no school", "closure", "break", "vacation")):
        return "holiday"
    if any(w in lower for w in ("staar", "test", "assessment", "benchmark", "map test")):
        return "testing"
    if any(w in lower for w in ("conference", "open house", "pta", "parent")):
        return "parent_event"
    if any(w in lower for w in ("field trip", "picture", "spirit", "performance", "concert")):
        return "school_event"
    if any(w in lower for w in ("deadline", "due", "registration", "enroll")):
        return "deadline"
    return "other"


def _strip_html(text: str) -> str:
    """Quick HTML tag stripper."""
    from bs4 import BeautifulSoup
    return BeautifulSoup(text, "lxml").get_text(separator=" ", strip=True)


def _parse_llm_events(raw_text: str) -> List[Dict[str, Any]]:
    """Parse LLM JSON response into event list."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                return []
        else:
            return []

    return data.get("events", [])
