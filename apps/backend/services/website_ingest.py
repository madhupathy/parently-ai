"""Website ingestion — crawl school pages, strip boilerplate, extract content.

Fetches school homepage and announcement pages, strips nav/footer/scripts,
extracts meaningful parent-facing content using LLM, and stores as Documents
in the RAG store.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from storage import get_db, rag_store
from storage.models import Document

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_USER_AGENT = "Parently-SchoolBot/1.0 (+https://parently.app)"


def ingest_school_website(
    school_source_id: int,
    child_id: int,
    homepage_url: Optional[str] = None,
    school_name: str = "School",
) -> Dict[str, Any]:
    """Ingest school website content into RAG store.

    Returns summary of ingestion results.
    """
    results = {
        "pages_fetched": 0,
        "announcements_extracted": 0,
        "documents_created": 0,
    }

    if not homepage_url:
        return results

    # Fetch homepage
    html = _fetch_text(homepage_url)
    if not html:
        return results
    results["pages_fetched"] += 1

    # Strip boilerplate and extract clean text
    clean_text = strip_boilerplate(html)
    if not clean_text or len(clean_text.strip()) < 50:
        logger.info("Homepage content too short after stripping: %s", homepage_url)
        return results

    # Extract announcements via LLM
    announcements = extract_announcements(clean_text, school_name, homepage_url)
    results["announcements_extracted"] = len(announcements)

    # Store as document
    if clean_text.strip():
        doc_id = _store_website_document(
            clean_text, announcements, school_name, homepage_url, child_id
        )
        results["documents_created"] += 1

    logger.info(
        "Website ingest for source %d: %s", school_source_id, results,
    )
    return results


def strip_boilerplate(html: str) -> str:
    """Strip nav, footer, scripts, styles, and other boilerplate from HTML."""
    soup = BeautifulSoup(html, "lxml")

    # Remove non-content elements
    for tag_name in ["nav", "footer", "header", "script", "style", "noscript",
                     "iframe", "form", "aside"]:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    # Remove common boilerplate class/id patterns
    for pattern in ["cookie", "banner", "popup", "modal", "sidebar", "menu",
                    "breadcrumb", "social", "share", "comment"]:
        for el in soup.find_all(class_=lambda c: c and pattern in str(c).lower()):
            el.decompose()
        for el in soup.find_all(id=lambda i: i and pattern in str(i).lower()):
            el.decompose()

    text = soup.get_text(separator="\n", strip=True)

    # Collapse excessive blank lines
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return "\n".join(lines)


def extract_announcements(
    clean_text: str,
    school_name: str,
    page_url: str,
) -> List[Dict[str, Any]]:
    """Extract structured announcements from page text using LLM."""
    from services.gemini import generate
    from services.prompt_loader import load_prompt

    # Truncate to avoid excessive token usage
    truncated = clean_text[:6000]

    system_prompt = load_prompt("website_extract_prompt_v1")
    user_prompt = json.dumps({
        "school_name": school_name,
        "page_url": page_url,
        "raw_content": truncated,
    })

    result = generate(prompt=user_prompt, system_instruction=system_prompt)
    if not result.text:
        return []

    return _parse_llm_announcements(result.text)


def _store_website_document(
    clean_text: str,
    announcements: List[Dict[str, Any]],
    school_name: str,
    source_url: str,
    child_id: int,
) -> int:
    """Store website content as a Document in the RAG store."""
    # Build combined text for embedding
    text_parts = [f"# Website Content — {school_name}\n"]
    text_parts.append(clean_text[:4000])

    if announcements:
        text_parts.append("\n\n## Announcements\n")
        for ann in announcements:
            title = ann.get("title", "Update")
            body = ann.get("body", "")
            date_str = ann.get("date", "")
            line = f"- **{title}**"
            if date_str:
                line += f" ({date_str})"
            if body:
                line += f": {body[:200]}"
            text_parts.append(line)

    text = "\n".join(text_parts)

    content_hash = hashlib.sha256(text.encode()).hexdigest()[:12]
    filename = f"website_{content_hash}.md"

    # Dedup check
    db = get_db()
    with db.session_scope() as session:
        existing = session.query(Document).filter(
            Document.filename == filename
        ).first()
        if existing:
            existing.text = text
            if hasattr(existing, "metadata_json"):
                existing.metadata_json = json.dumps({
                    "source_type": "web_page",
                    "source_url": source_url,
                    "child_id": child_id,
                    "school_name": school_name,
                    "announcement_count": len(announcements),
                    "announcements": announcements,
                    "updated_at": datetime.utcnow().isoformat(),
                })
            return existing.id

    doc_id = rag_store.add_document(filename, "text/markdown", text)

    with db.session_scope() as session:
        doc = session.query(Document).filter(Document.id == doc_id).first()
        if doc and hasattr(doc, "metadata_json"):
            doc.metadata_json = json.dumps({
                "source_type": "web_page",
                "source_url": source_url,
                "child_id": child_id,
                "school_name": school_name,
                "announcement_count": len(announcements),
                "announcements": announcements,
            })

    return doc_id


# ---------------------------------------------------------------------------
# Helpers
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


def _parse_llm_announcements(raw_text: str) -> List[Dict[str, Any]]:
    """Parse LLM JSON response into announcements list."""
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

    return data.get("announcements", [])
