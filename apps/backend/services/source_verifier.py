"""Source verifier — scores candidate school sites and auto-persists verified ones.

Deterministic scoring (0–1):
  +0.25 if page title contains school tokens
  +0.20 if calendar page exists and reachable
  +0.20 if ICS or RSS link found
  +0.15 if district calendar PDF found
  +0.10 if domain matches expected pattern (.org/.edu/.k12)
  -0.20 if tokens mismatch (wrong city/state)

If score is in the gray zone (0.55–0.75), optionally calls LLM verifier.
If score >= 0.82, auto-persists as "verified".
If score < 0.82, saves as "needs_confirmation".
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

from services.prompt_loader import load_context, load_prompt
from services.school_discovery import tokenize_school_query

logger = logging.getLogger(__name__)

AUTO_VERIFY_THRESHOLD = 0.82
GRAY_ZONE_LOW = 0.55
GRAY_ZONE_HIGH = 0.75


def score_candidate(
    candidate: Dict[str, Any],
    fetch_result: Dict[str, Any],
    school_query: str,
    context: Optional[Dict[str, Any]] = None,
) -> float:
    """Compute a deterministic confidence score for a candidate.

    Args:
        candidate: LLM candidate dict (name, homepage_url, etc.)
        fetch_result: Site fetcher output (snippets, found_ics_links, etc.)
        school_query: Original user school text.
        context: Shared context (auto-loaded if None).

    Returns:
        Score between 0.0 and 1.0.
    """
    if context is None:
        context = load_context()

    parsed = tokenize_school_query(school_query)
    school_tokens = [t.lower() for t in parsed["school_tokens"]]
    city = (parsed.get("city") or "").lower()
    state = (parsed.get("state") or "").lower()

    score = 0.0

    # +0.25: page title / snippets contain school tokens
    snippets_lower = " ".join(s.lower() for s in fetch_result.get("snippets", []))
    matching_tokens = sum(1 for t in school_tokens if t in snippets_lower)
    if school_tokens and matching_tokens >= len(school_tokens) * 0.5:
        score += 0.25
    elif matching_tokens > 0:
        score += 0.12

    # +0.20: calendar page exists and was reachable
    if fetch_result.get("found_calendar_pages"):
        score += 0.20

    # +0.20: ICS or RSS link found
    if fetch_result.get("found_ics_links") or fetch_result.get("found_rss_links"):
        score += 0.20

    # +0.15: district calendar PDF found
    if fetch_result.get("found_pdf_links"):
        score += 0.15

    # +0.10: domain matches expected pattern
    homepage_url = candidate.get("homepage_url", "")
    domain = urlparse(homepage_url).netloc.lower() if homepage_url else ""
    preferred_patterns = context.get("school_site_preference_domains", [])
    if any(pat in domain for pat in preferred_patterns):
        score += 0.10

    # -0.20: city/state mismatch
    if city and city not in snippets_lower and state and state not in snippets_lower:
        candidate_name = (candidate.get("name") or "").lower()
        if city not in candidate_name:
            score -= 0.20

    # Clamp
    score = max(0.0, min(1.0, score))

    logger.debug(
        "Scored candidate '%s': %.2f (tokens=%d/%d matched, cal=%s, ics=%s, rss=%s, pdf=%s, domain=%s)",
        candidate.get("name", "?"), score,
        matching_tokens, len(school_tokens),
        bool(fetch_result.get("found_calendar_pages")),
        bool(fetch_result.get("found_ics_links")),
        bool(fetch_result.get("found_rss_links")),
        bool(fetch_result.get("found_pdf_links")),
        domain,
    )
    return score


def verify_with_llm(
    candidate: Dict[str, Any],
    fetch_result: Dict[str, Any],
    school_query: str,
    deterministic_score: float,
) -> Tuple[bool, float]:
    """Optional LLM verification for gray-zone candidates.

    Only called when deterministic_score is between 0.55 and 0.75.

    Returns:
        (is_match, confidence) tuple.
    """
    from services.gemini import generate

    system_prompt = load_prompt("source_verifier_prompt_v1")
    user_prompt = json.dumps({
        "school_query": school_query,
        "candidate": {
            "name": candidate.get("name"),
            "homepage_url": candidate.get("homepage_url"),
            "calendar_page_url": candidate.get("calendar_page_url"),
            "snippets": fetch_result.get("snippets", [])[:10],
        },
        "deterministic_score": round(deterministic_score, 3),
    }, indent=2)

    result = generate(prompt=user_prompt, system_instruction=system_prompt)
    if not result.text:
        return False, deterministic_score

    try:
        text = result.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        data = json.loads(text)
        return data.get("is_match", False), data.get("confidence", deterministic_score)
    except (json.JSONDecodeError, KeyError):
        logger.warning("Failed to parse LLM verifier response")
        return False, deterministic_score


def score_and_classify(
    candidate: Dict[str, Any],
    fetch_result: Dict[str, Any],
    school_query: str,
    use_llm_for_gray_zone: bool = True,
) -> Tuple[float, str]:
    """Score a candidate and determine its status.

    Returns:
        (score, status) where status is "verified", "needs_confirmation", or "failed".
    """
    ctx = load_context()
    score = score_candidate(candidate, fetch_result, school_query, context=ctx)

    # HTTP failure = failed
    if fetch_result.get("http_status") is None or fetch_result.get("error"):
        if score < 0.3:
            return score, "failed"

    if score >= AUTO_VERIFY_THRESHOLD:
        return score, "verified"

    # Gray zone — optional LLM verification
    if use_llm_for_gray_zone and GRAY_ZONE_LOW <= score <= GRAY_ZONE_HIGH:
        is_match, llm_confidence = verify_with_llm(
            candidate, fetch_result, school_query, score
        )
        if is_match and llm_confidence >= AUTO_VERIFY_THRESHOLD:
            return llm_confidence, "verified"

    if score < 0.3:
        return score, "failed"

    return score, "needs_confirmation"
