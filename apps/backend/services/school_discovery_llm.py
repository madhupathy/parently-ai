"""LLM-based school discovery — calls Gemini to identify candidate school URLs.

Uses the school_discovery_prompt_v1.md prompt with search queries from
school_discovery.build_search_queries().

Returns up to 3 structured candidate objects with homepage, calendar, and
district URLs.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from services.gemini import generate
from services.prompt_loader import load_context, load_prompt
from services.school_discovery import build_search_queries

logger = logging.getLogger(__name__)


def discover_school_candidates(
    school_query: str,
    max_candidates: int = 3,
) -> List[Dict[str, Any]]:
    """Run LLM school discovery and return candidate objects.

    Args:
        school_query: The user's school text (e.g. "Harmony Georgetown, Georgetown, TX 78628")
        max_candidates: Max candidates to return (default 3).

    Returns:
        List of candidate dicts, each with:
          name, homepage_url, district_site_url, calendar_page_url, notes
    """
    ctx = load_context()
    search_terms = build_search_queries(school_query, max_queries=6)

    # Build the system prompt from versioned template
    system_prompt = load_prompt("school_discovery_prompt_v1", context=ctx)

    # Build the user prompt with the actual query + terms
    user_prompt = json.dumps({
        "school_query": school_query,
        "search_terms": search_terms,
    }, indent=2)

    logger.info("Running school discovery LLM for query: %s", school_query)

    result = generate(
        prompt=user_prompt,
        system_instruction=system_prompt,
    )

    if not result.text:
        logger.warning("LLM returned empty response for school discovery")
        return []

    candidates = _parse_candidates(result.text, max_candidates)
    logger.info(
        "School discovery returned %d candidates (model=%s, cost=$%.6f)",
        len(candidates), result.model, result.estimated_cost_usd,
    )
    return candidates


def _parse_candidates(
    raw_text: str,
    max_candidates: int,
) -> List[Dict[str, Any]]:
    """Parse LLM response into structured candidate list.

    Handles various LLM output quirks: markdown code fences, trailing text, etc.
    """
    text = raw_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first line (```json or ```) and last line (```)
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON object in the text
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                logger.error("Failed to parse LLM school discovery response")
                return []
        else:
            logger.error("No JSON found in LLM school discovery response")
            return []

    candidates = data.get("candidates", [])
    if not isinstance(candidates, list):
        logger.error("LLM response 'candidates' is not a list")
        return []

    # Normalize and validate
    result: List[Dict[str, Any]] = []
    for c in candidates[:max_candidates]:
        if not isinstance(c, dict):
            continue
        result.append({
            "name": c.get("name", "Unknown"),
            "homepage_url": c.get("homepage_url"),
            "district_site_url": c.get("district_site_url"),
            "calendar_page_url": c.get("calendar_page_url"),
            "notes": c.get("notes", ""),
        })

    return result
