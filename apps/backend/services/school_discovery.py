"""School discovery query builder.

Tokenizes a user's free-text school query into multiple expanded search
terms suitable for LLM-based school identification.

Example:
    Input:  "Harmony Georgetown, Georgetown, TX 78628"
    Output: [
        "Harmony Science Academy Georgetown TX",
        "Harmony Georgetown campus calendar",
        "HSA Georgetown calendar",
        "Harmony Georgetown academic calendar PDF",
        "Harmony Georgetown calendar feed ICS",
        "Harmony Georgetown district calendar",
    ]
"""

from __future__ import annotations

import logging
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Common school name abbreviation expansions
_ABBREVIATIONS: Dict[str, List[str]] = {
    "harmony": ["Harmony Science Academy", "HSA"],
    "kipp": ["KIPP", "Knowledge Is Power Program"],
    "idea": ["IDEA Public Schools", "IDEA"],
    "basis": ["BASIS", "BASIS Charter Schools"],
    "montessori": ["Montessori"],
    "stem": ["STEM Academy", "STEM"],
    "hsa": ["Harmony Science Academy", "HSA"],
    "gisd": ["Georgetown ISD"],
    "rrisd": ["Round Rock ISD"],
    "aisd": ["Austin ISD"],
    "lisd": ["Leander ISD"],
    "pisd": ["Pflugerville ISD"],
}

# US state abbreviation map (subset — common ones)
_STATE_ABBREVS: Dict[str, str] = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho",
    "IL": "Illinois", "IN": "Indiana", "IA": "Iowa", "KS": "Kansas",
    "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma",
    "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah",
    "VT": "Vermont", "VA": "Virginia", "WA": "Washington", "WV": "West Virginia",
    "WI": "Wisconsin", "WY": "Wyoming",
}


def tokenize_school_query(query: str) -> Dict[str, any]:
    """Parse a school query into structured tokens.

    Returns dict with keys: school_tokens, city, state, zip_code, raw.
    """
    raw = query.strip()
    # Normalize: collapse whitespace, strip trailing punctuation
    normalized = re.sub(r"\s+", " ", raw).strip(" ,.")

    # Try to extract zip code (5-digit or 5+4)
    zip_match = re.search(r"\b(\d{5})(?:-\d{4})?\b", normalized)
    zip_code = zip_match.group(1) if zip_match else None

    # Try to extract state abbreviation (2 uppercase letters preceded by comma or space)
    state = None
    state_match = re.search(r"[,\s]+([A-Z]{2})\b", normalized)
    if state_match and state_match.group(1) in _STATE_ABBREVS:
        state = state_match.group(1)

    # Try to extract city — typically after the first comma, before state
    parts = [p.strip() for p in normalized.split(",")]
    city = None
    school_text = parts[0]
    if len(parts) >= 2:
        # Second part is usually city or city+state
        city_state = parts[1].strip()
        # Remove state and zip from city_state
        city_candidate = re.sub(r"\b[A-Z]{2}\b", "", city_state)
        city_candidate = re.sub(r"\b\d{5}(-\d{4})?\b", "", city_candidate)
        city_candidate = city_candidate.strip(" ,.")
        if city_candidate:
            city = city_candidate

    # School tokens: split school text, remove pure numbers and very short noise
    school_tokens = [
        t for t in school_text.split()
        if len(t) > 1 and not t.isdigit()
    ]

    return {
        "school_tokens": school_tokens,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "raw": raw,
    }


def expand_abbreviations(tokens: List[str]) -> List[str]:
    """Return expanded school name variants from known abbreviations."""
    expansions: List[str] = []
    for token in tokens:
        key = token.lower()
        if key in _ABBREVIATIONS:
            expansions.extend(_ABBREVIATIONS[key])
    return expansions


def build_search_queries(query: str, max_queries: int = 6) -> List[str]:
    """Build a list of search queries from a school text input.

    Args:
        query: Free-text school input (e.g. "Harmony Georgetown, Georgetown, TX 78628")
        max_queries: Max queries to return.

    Returns:
        List of search query strings for LLM consumption.
    """
    parsed = tokenize_school_query(query)
    school_tokens = parsed["school_tokens"]
    city = parsed["city"]
    state = parsed["state"]
    zip_code = parsed["zip_code"]

    school_name = " ".join(school_tokens)
    location_suffix = " ".join(filter(None, [city, state]))

    queries: List[str] = []

    # 1. Expanded full name + location + state
    expansions = expand_abbreviations(school_tokens)
    if expansions:
        for exp in expansions[:2]:  # take top 2 expansions
            q = f"{exp} {location_suffix}".strip()
            if q and q not in queries:
                queries.append(q)

    # 2. Original school tokens + location
    base = f"{school_name} {location_suffix}".strip()
    if base and base not in queries:
        queries.append(base)

    # 3. School name + "campus calendar"
    q3 = f"{school_name} campus calendar"
    if q3 not in queries:
        queries.append(q3)

    # 4. Abbreviation + location + "calendar"
    if expansions:
        abbr = expansions[0].split()[-1] if len(expansions[0].split()) > 1 else expansions[0]
        q4 = f"{abbr} {city or ''} calendar".strip()
        if q4 and q4 not in queries:
            queries.append(q4)

    # 5. School name + "academic calendar PDF"
    q5 = f"{school_name} academic calendar PDF"
    if q5 not in queries:
        queries.append(q5)

    # 6. School name + "calendar feed ICS"
    q6 = f"{school_name} calendar feed ICS"
    if q6 not in queries:
        queries.append(q6)

    # 7. School name + "district calendar"
    q7 = f"{school_name} district calendar"
    if q7 not in queries:
        queries.append(q7)

    # Trim to max
    result = queries[:max_queries]
    logger.debug("Built %d search queries from '%s': %s", len(result), query, result)
    return result
