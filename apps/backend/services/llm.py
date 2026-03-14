"""LLM integration for digest summarization.

Uses Gemini 1.5 Flash as primary, OpenAI GPT-4o-mini as fallback,
and a template-based summary as last resort.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from config import get_settings
from services.gemini import LLMResult, generate as gemini_generate

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Parently, a calm and helpful AI assistant for busy parents.
You receive a list of school-related items (emails, documents, grades, messages)
and produce a concise, friendly daily digest in Markdown.

Rules:
- Group items by priority: action-required first, then informational
- Use clear headings and bullet points
- Highlight due dates and deadlines
- Keep the tone warm but concise
- If there are action items, list them clearly at the top
- End with a brief encouraging note"""


def summarize_digest(
    items: List[Dict[str, Any]],
    user_api_key: Optional[str] = None,
    user_model: Optional[str] = None,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Summarize digest items using Gemini (primary) or OpenAI (fallback).

    Returns (markdown_text, usage_dict_or_None).
    """
    settings = get_settings()
    has_llm = settings.gemini_api_key or settings.openai_api_key or user_api_key

    if not has_llm:
        logger.info("No LLM API key available, using template summary")
        return _template_summary(items), None

    items_text = json.dumps(items, indent=2, default=str)
    prompt = (
        "Here are today's school-related items for my children. "
        f"Please create a friendly daily digest summary:\n\n{items_text}"
    )

    try:
        result: LLMResult = gemini_generate(prompt, system_instruction=SYSTEM_PROMPT)
        if result.text:
            return result.text, {
                "model": result.model,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "estimated_cost_usd": result.estimated_cost_usd,
            }
    except Exception as exc:
        logger.warning("LLM summarization failed, falling back to template: %s", exc)

    return _template_summary(items), None


def _template_summary(items: List[Dict[str, Any]]) -> str:
    """Simple template-based summary when Ollama is unavailable."""
    if not items:
        return "### No new updates\n\nEverything is quiet today. Enjoy your day!"

    action_items = [i for i in items if "action" in i.get("tags", [])]
    finance_items = [i for i in items if "finance" in i.get("tags", [])]
    event_items = [i for i in items if "event" in i.get("tags", [])]
    other_items = [
        i for i in items
        if not any(t in i.get("tags", []) for t in ("action", "finance", "event"))
    ]

    lines = ["# Parently Daily Digest", ""]

    if action_items:
        lines.append("## Action Required")
        for item in action_items:
            due = item.get("due_date") or "TBD"
            lines.append(f"- **{item.get('subject', 'Update')}** — Due: {due}")
            body = item.get("body", "")
            if body:
                lines.append(f"  {body[:150]}")
        lines.append("")

    if finance_items:
        lines.append("## Payments & Fees")
        for item in finance_items:
            lines.append(f"- **{item.get('subject', 'Payment')}**")
            body = item.get("body", "")
            if body:
                lines.append(f"  {body[:150]}")
        lines.append("")

    if event_items:
        lines.append("## Upcoming Events")
        for item in event_items:
            due = item.get("due_date") or ""
            lines.append(f"- **{item.get('subject', 'Event')}** {due}")
            body = item.get("body", "")
            if body:
                lines.append(f"  {body[:150]}")
        lines.append("")

    if other_items:
        lines.append("## Other Updates")
        for item in other_items:
            source = item.get("source", "")
            lines.append(f"- **{item.get('subject', 'Update')}** ({source})")
            body = item.get("body", "")
            if body:
                lines.append(f"  {body[:150]}")
        lines.append("")

    lines.append("---")
    lines.append("*Have a great day!*")

    return "\n".join(lines)
