"""Site fetcher — crawls candidate school domains to discover calendar assets.

For each candidate URL:
  1. GET homepage → extract title, H1/H2 snippets, footer text
  2. Find calendar links (anchor text + href patterns)
  3. On calendar page: find .ics, RSS, PDF links
  4. Return structured extraction result

Respects polite_delay_ms from common_context.json.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from services.prompt_loader import load_context

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0
_USER_AGENT = "Parently-SchoolBot/1.0 (+https://parently.app)"


def fetch_candidate(
    candidate: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Crawl a single candidate school site and discover assets.

    Args:
        candidate: Dict with homepage_url, calendar_page_url (optional).
        context: Shared context (loaded automatically if None).

    Returns:
        Dict with found_calendar_pages, found_ics_links, found_rss_links,
        found_pdf_links, snippets, http_status.
    """
    if context is None:
        context = load_context()

    delay_s = context.get("polite_delay_ms", 800) / 1000.0
    max_pages = context.get("max_pages_per_domain", 5)
    calendar_hints = context.get("calendar_link_hints", [])
    doc_hints = context.get("school_doc_hints", [])

    homepage_url = candidate.get("homepage_url")
    provided_calendar = candidate.get("calendar_page_url")

    result: Dict[str, Any] = {
        "candidate_homepage": homepage_url,
        "found_calendar_pages": [],
        "found_ics_links": [],
        "found_rss_links": [],
        "found_pdf_links": [],
        "snippets": [],
        "http_status": None,
        "error": None,
    }

    if not homepage_url:
        result["error"] = "No homepage URL provided"
        return result

    pages_fetched = 0
    visited: set = set()

    # Step 1: Fetch homepage
    homepage_html, status = _fetch_page(homepage_url)
    result["http_status"] = status
    if not homepage_html:
        result["error"] = f"Failed to fetch homepage (status={status})"
        return result

    pages_fetched += 1
    visited.add(_normalize_url(homepage_url))

    # Extract snippets from homepage
    soup = BeautifulSoup(homepage_html, "lxml")
    result["snippets"] = _extract_snippets(soup)

    # Find calendar page links on homepage
    calendar_links = _find_calendar_links(soup, homepage_url, calendar_hints)
    result["found_calendar_pages"] = list(set(calendar_links))

    # If candidate provided a calendar URL, add it
    if provided_calendar and provided_calendar not in calendar_links:
        calendar_links.insert(0, provided_calendar)

    # Step 2: Crawl calendar pages
    for cal_url in calendar_links:
        if pages_fetched >= max_pages:
            break
        norm = _normalize_url(cal_url)
        if norm in visited:
            continue

        time.sleep(delay_s)
        cal_html, cal_status = _fetch_page(cal_url)
        pages_fetched += 1
        visited.add(norm)

        if not cal_html:
            continue

        cal_soup = BeautifulSoup(cal_html, "lxml")

        # Extract ICS links
        ics_links = _find_links_by_pattern(cal_soup, cal_url, [".ics", "ical"])
        result["found_ics_links"].extend(ics_links)

        # Extract RSS links
        rss_links = _find_rss_links(cal_soup, cal_url)
        result["found_rss_links"].extend(rss_links)

        # Extract PDF links
        pdf_links = _find_links_by_pattern(cal_soup, cal_url, [".pdf"])
        result["found_pdf_links"].extend(pdf_links)

        # Extract more snippets
        extra_snippets = _extract_snippets(cal_soup)
        result["snippets"].extend(extra_snippets)

    # Deduplicate
    result["found_ics_links"] = list(set(result["found_ics_links"]))
    result["found_rss_links"] = list(set(result["found_rss_links"]))
    result["found_pdf_links"] = list(set(result["found_pdf_links"]))
    result["snippets"] = list(set(result["snippets"]))[:20]

    logger.info(
        "Fetched candidate %s: status=%s, calendars=%d, ics=%d, rss=%d, pdf=%d",
        homepage_url, status,
        len(result["found_calendar_pages"]),
        len(result["found_ics_links"]),
        len(result["found_rss_links"]),
        len(result["found_pdf_links"]),
    )

    return result


def fetch_all_candidates(
    candidates: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Fetch all candidate sites and return extraction results."""
    ctx = load_context()
    delay_s = ctx.get("polite_delay_ms", 800) / 1000.0
    results = []
    for i, candidate in enumerate(candidates):
        if i > 0:
            time.sleep(delay_s)
        results.append(fetch_candidate(candidate, context=ctx))
    return results


# --- Internal helpers ---

def _fetch_page(url: str) -> tuple:
    """Fetch a URL and return (html_text, status_code)."""
    try:
        with httpx.Client(
            timeout=_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENT},
        ) as client:
            resp = client.get(url)
            return resp.text, resp.status_code
    except Exception as exc:
        logger.debug("Failed to fetch %s: %s", url, exc)
        return None, None


def _normalize_url(url: str) -> str:
    """Normalize URL for dedup (lowercase host, strip fragment)."""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path}".rstrip("/")


def _extract_snippets(soup: BeautifulSoup) -> List[str]:
    """Extract title and heading text from a page."""
    snippets = []
    title = soup.find("title")
    if title and title.string:
        snippets.append(title.string.strip()[:200])

    for tag in soup.find_all(["h1", "h2", "h3"], limit=10):
        text = tag.get_text(strip=True)[:200]
        if text and len(text) > 3:
            snippets.append(text)

    return snippets


def _find_calendar_links(
    soup: BeautifulSoup,
    base_url: str,
    hints: List[str],
) -> List[str]:
    """Find links that look like calendar pages."""
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True).lower()
        href_lower = href.lower()

        is_calendar = False
        # Check anchor text
        for hint in ["calendar", "events", "district calendar", "academic calendar"]:
            if hint in text:
                is_calendar = True
                break
        # Check href patterns
        if not is_calendar:
            for hint in hints:
                if hint in href_lower:
                    is_calendar = True
                    break

        if is_calendar:
            full_url = urljoin(base_url, href)
            if full_url not in links:
                links.append(full_url)

    return links[:10]


def _find_links_by_pattern(
    soup: BeautifulSoup,
    base_url: str,
    patterns: List[str],
) -> List[str]:
    """Find links whose href matches any of the given patterns."""
    links = []
    for a in soup.find_all("a", href=True):
        href_lower = a["href"].lower()
        for pat in patterns:
            if pat in href_lower:
                full_url = urljoin(base_url, a["href"])
                links.append(full_url)
                break

    # Also check link tags (e.g., <link rel="alternate" type="text/calendar">)
    for link in soup.find_all("link", href=True):
        href_lower = link["href"].lower()
        for pat in patterns:
            if pat in href_lower:
                full_url = urljoin(base_url, link["href"])
                links.append(full_url)
                break

    return links


def _find_rss_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Find RSS/Atom feed links."""
    links = []

    # Standard <link> tags
    for link in soup.find_all("link", type=True):
        link_type = link.get("type", "").lower()
        if "rss" in link_type or "atom" in link_type or "xml" in link_type:
            href = link.get("href")
            if href:
                links.append(urljoin(base_url, href))

    # Anchor links with RSS hints
    for a in soup.find_all("a", href=True):
        href_lower = a["href"].lower()
        text_lower = a.get_text(strip=True).lower()
        if "rss" in href_lower or "feed" in href_lower or "rss" in text_lower:
            links.append(urljoin(base_url, a["href"]))

    return links
