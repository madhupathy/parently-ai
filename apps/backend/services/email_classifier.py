"""Email platform classifier — tag school emails by platform and extract events.

Two-pass classification:
  1. Deterministic: check sender domain against known platform domains
  2. LLM fallback: classify ambiguous emails using prompt

Supported platforms: ClassDojo, Brightwheel, Kumon, Skyward, school_direct.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from services.prompt_loader import load_context

logger = logging.getLogger(__name__)


def classify_email(
    sender: str,
    subject: str,
    snippet: str,
    body: Optional[str] = None,
    child_names: Optional[List[str]] = None,
    school_names: Optional[List[str]] = None,
    use_llm: bool = True,
) -> Dict[str, Any]:
    """Classify a single email by platform and extract events.

    Args:
        sender: Sender email address.
        subject: Email subject line.
        snippet: Email snippet/preview.
        body: Full email body text (may be None).
        child_names: List of user's children's names.
        school_names: List of known school names.
        use_llm: Whether to use LLM for ambiguous emails.

    Returns:
        Classification dict with platform, confidence, child_match, extracted events.
    """
    ctx = load_context()
    platform_domains = ctx.get("email_platform_domains", {})

    # Pass 1: Deterministic domain check
    sender_domain = _extract_domain(sender)
    for platform, domains in platform_domains.items():
        for domain in domains:
            if domain in sender_domain:
                result = {
                    "platform": platform,
                    "confidence": 0.95,
                    "child_match": _match_child(subject, snippet, body, child_names),
                    "child_match_confidence": 0.0,
                    "extracted": {
                        "events": [],
                        "is_actionable": _is_actionable(subject, snippet),
                        "urgency": _estimate_urgency(subject, snippet),
                    },
                    "classification_method": "domain",
                }
                # Try to extract events from subject/snippet
                result["extracted"]["events"] = _extract_basic_events(subject, snippet)
                if result["child_match"]:
                    result["child_match_confidence"] = 0.8
                return result

    # Check for school-direct domains
    if sender_domain and _is_school_domain(sender_domain):
        result = {
            "platform": "school_direct",
            "confidence": 0.80,
            "child_match": _match_child(subject, snippet, body, child_names),
            "child_match_confidence": 0.0,
            "extracted": {
                "events": _extract_basic_events(subject, snippet),
                "is_actionable": _is_actionable(subject, snippet),
                "urgency": _estimate_urgency(subject, snippet),
            },
            "classification_method": "domain",
        }
        if result["child_match"]:
            result["child_match_confidence"] = 0.7
        return result

    # Pass 2: LLM classification for ambiguous emails
    if use_llm and (subject or snippet):
        return _classify_with_llm(
            sender, subject, snippet, body,
            child_names or [], school_names or [],
        )

    return {
        "platform": "unknown",
        "confidence": 0.0,
        "child_match": None,
        "child_match_confidence": 0.0,
        "extracted": {
            "events": [],
            "is_actionable": False,
            "urgency": "low",
        },
        "classification_method": "none",
    }


def classify_emails_batch(
    emails: List[Dict[str, Any]],
    child_names: Optional[List[str]] = None,
    school_names: Optional[List[str]] = None,
    use_llm: bool = True,
) -> List[Dict[str, Any]]:
    """Classify a batch of emails.

    Each email dict should have: sender, subject, snippet, body (optional).
    Returns list of classification results with original email data attached.
    """
    results = []
    for email in emails:
        classification = classify_email(
            sender=email.get("sender", email.get("from_email", "")),
            subject=email.get("subject", ""),
            snippet=email.get("snippet", ""),
            body=email.get("body"),
            child_names=child_names,
            school_names=school_names,
            use_llm=use_llm,
        )
        classification["email"] = {
            "sender": email.get("sender", email.get("from_email", "")),
            "subject": email.get("subject", ""),
            "snippet": email.get("snippet", ""),
        }
        results.append(classification)
    return results


# ---------------------------------------------------------------------------
# LLM classification
# ---------------------------------------------------------------------------

def _classify_with_llm(
    sender: str,
    subject: str,
    snippet: str,
    body: Optional[str],
    child_names: List[str],
    school_names: List[str],
) -> Dict[str, Any]:
    """Classify email using LLM prompt."""
    from services.gemini import generate
    from services.prompt_loader import load_prompt

    system_prompt = load_prompt("email_school_classifier_prompt_v1")
    user_prompt = json.dumps({
        "sender": sender,
        "subject": subject,
        "snippet": snippet,
        "body": (body or "")[:3000],
        "child_names": child_names,
        "school_names": school_names,
    })

    result = generate(prompt=user_prompt, system_instruction=system_prompt)
    if not result.text:
        return {
            "platform": "unknown",
            "confidence": 0.0,
            "child_match": None,
            "child_match_confidence": 0.0,
            "extracted": {"events": [], "is_actionable": False, "urgency": "low"},
            "classification_method": "llm_failed",
        }

    parsed = _parse_llm_classification(result.text)
    parsed["classification_method"] = "llm"
    return parsed


def _parse_llm_classification(raw_text: str) -> Dict[str, Any]:
    """Parse LLM classification response."""
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines).strip()

    default = {
        "platform": "unknown",
        "confidence": 0.0,
        "child_match": None,
        "child_match_confidence": 0.0,
        "extracted": {"events": [], "is_actionable": False, "urgency": "low"},
    }

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                data = json.loads(text[start:end])
            except json.JSONDecodeError:
                return default
        else:
            return default

    return {
        "platform": data.get("platform", "unknown"),
        "confidence": data.get("confidence", 0.0),
        "child_match": data.get("child_match"),
        "child_match_confidence": data.get("child_match_confidence", 0.0),
        "extracted": data.get("extracted", default["extracted"]),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_domain(email_addr: str) -> str:
    """Extract domain from an email address."""
    if "@" in email_addr:
        return email_addr.split("@", 1)[1].lower()
    return email_addr.lower()


def _is_school_domain(domain: str) -> bool:
    """Check if a domain looks like a school domain."""
    school_patterns = [".k12.", ".edu", ".org"]
    return any(pat in domain for pat in school_patterns)


def _match_child(
    subject: str,
    snippet: str,
    body: Optional[str],
    child_names: Optional[List[str]],
) -> Optional[str]:
    """Try to match email content to a child by name."""
    if not child_names:
        return None
    combined = f"{subject} {snippet} {body or ''}".lower()
    for name in child_names:
        if name.lower() in combined:
            return name
    return None


def _is_actionable(subject: str, snippet: str) -> bool:
    """Check if email appears to require parent action."""
    combined = (subject + " " + snippet).lower()
    action_words = [
        "sign", "pay", "rsvp", "bring", "pack", "submit", "return",
        "permission", "form", "fee", "due", "required", "action needed",
        "reminder", "don't forget", "important",
    ]
    return any(w in combined for w in action_words)


def _estimate_urgency(subject: str, snippet: str) -> str:
    """Estimate urgency from subject/snippet."""
    combined = (subject + " " + snippet).lower()
    if any(w in combined for w in ("urgent", "asap", "today", "immediately", "emergency")):
        return "high"
    if any(w in combined for w in ("tomorrow", "this week", "reminder", "don't forget")):
        return "medium"
    return "low"


def _extract_basic_events(subject: str, snippet: str) -> List[Dict[str, Any]]:
    """Extract basic event hints from subject/snippet without LLM."""
    events = []
    if subject:
        events.append({
            "title": subject,
            "date": None,
            "type": "message",
            "summary": snippet[:200] if snippet else "",
        })
    return events
