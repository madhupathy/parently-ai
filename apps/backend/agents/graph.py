"""LangGraph workflow powering Parently digests.

Pipeline:
  fetch_gmail → fetch_connectors → fetch_school_sources → classify_emails →
  parse_pdfs → rag_retrieve → extract_actions →
  compose_digest (per-child grouped via prompt)
"""

from __future__ import annotations

import json
import logging
from functools import wraps
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Sequence, TypedDict

from dateutil import parser as date_parser
from langgraph.graph import END, StateGraph

from config import get_settings
from services import gmail
from services.connectors import CONNECTORS
from services.connectors.base import DigestItem
from services.llm import summarize_digest
from storage import get_db, rag_store
from storage.models import Child, Document, SchoolSource, UserIntegration

logger = logging.getLogger(__name__)


class DigestStateDict(TypedDict, total=False):
    user_context: Dict[str, Any]
    gmail_messages: List[Dict[str, Any]]
    gmail_by_child: List[Dict[str, Any]]
    connector_items: List[Dict[str, Any]]
    pdf_texts: List[str]
    retrieved_context: List[Dict[str, Any]]
    extracted_items: List[Dict[str, Any]]
    school_events_by_child: Dict[int, List[Dict[str, Any]]]
    school_docs_by_child: Dict[int, List[Dict[str, Any]]]
    announcements_by_child: Dict[int, List[Dict[str, Any]]]
    classified_emails: List[Dict[str, Any]]
    children_map: Dict[int, str]
    digest_markdown: str
    llm_usage: Optional[Dict[str, Any]]


def _default_state(payload: Optional[Dict[str, Any]] = None) -> DigestStateDict:
    return {
        "user_context": payload or {},
        "gmail_messages": [],
        "gmail_by_child": [],
        "connector_items": [],
        "pdf_texts": [],
        "retrieved_context": [],
        "extracted_items": [],
        "school_events_by_child": {},
        "school_docs_by_child": {},
        "announcements_by_child": {},
        "classified_emails": [],
        "children_map": {},
        "digest_markdown": "",
        "llm_usage": None,
    }


class DigestState:
    """Attribute-friendly adapter over LangGraph dict state."""

    def __init__(self, raw_state: DigestStateDict):
        object.__setattr__(self, "_state", raw_state)
        defaults = _default_state()
        for key, value in defaults.items():
            self._state.setdefault(key, value)

    def __getattr__(self, name: str) -> Any:
        return self._state[name]

    def __setattr__(self, name: str, value: Any) -> None:
        self._state[name] = value

    def as_dict(self) -> DigestStateDict:
        return self._state


def _state_node(fn: Callable[[DigestState], DigestState]) -> Callable[[DigestStateDict], DigestStateDict]:
    @wraps(fn)
    def wrapped(state: DigestStateDict) -> DigestStateDict:
        digest_state = DigestState(state)
        result = fn(digest_state)
        if isinstance(result, DigestState):
            return result.as_dict()
        if isinstance(result, dict):
            return result
        raise TypeError(f"{fn.__name__} must return dict-compatible state, got {type(result)!r}")

    return wrapped


@_state_node
def fetch_gmail_node(state: DigestState) -> DigestState:
    """Fetch Gmail messages — targeted per-child if children exist, else legacy.

    If the user has children with search profiles, uses targeted sync
    (per-child queries, incremental dedup via GmailMessageIndex).
    Otherwise falls back to the legacy broad fetch.
    """
    user_id = state.user_context.get("user_id")
    email = state.user_context.get("email")

    # Try targeted sync if we have a user_id
    if user_id:
        try:
            from services.targeted_sync import sync_gmail_for_user
            child_results = sync_gmail_for_user(user_id)
            if child_results:
                state.gmail_by_child = child_results
                # Also flatten into gmail_messages for backward compat
                for group in child_results:
                    state.gmail_messages.extend(group.get("messages", []))
                logger.info(
                    "Targeted sync: %d child groups, %d total messages",
                    len(child_results), len(state.gmail_messages),
                )
                return state
        except Exception as exc:
            logger.warning("Targeted sync failed, falling back to legacy: %s", exc)

    # Legacy fallback: check for Gmail connector first
    if email:
        db = get_db()
        with db.session_scope() as session:
            has_gmail_connector = (
                session.query(UserIntegration)
                .filter(UserIntegration.user.has(email=email))
                .filter(UserIntegration.platform == "gmail")
                .filter(UserIntegration.status == "connected")
                .first()
            )
            if has_gmail_connector:
                logger.info("Gmail connector configured — skipping legacy fetch")
                return state

    logger.info("Fetching Gmail messages via legacy token path")
    state.gmail_messages = gmail.fetch_messages(max_results=10, user_id=user_id)
    return state


@_state_node
def fetch_connectors_node(state: DigestState) -> DigestState:
    """Run all configured connectors for the requesting user."""
    logger.info("Fetching updates from platform connectors")
    email = state.user_context.get("email")
    if not email:
        logger.debug("No user email in context, skipping connectors")
        return state

    db = get_db()
    with db.session_scope() as session:
        integrations = (
            session.query(UserIntegration)
            .filter(UserIntegration.user.has(email=email))
            .filter(UserIntegration.status == "connected")
            .all()
        )

        for integration in integrations:
            platform = integration.platform
            connector_cls = CONNECTORS.get(platform)
            if not connector_cls:
                logger.debug("No connector for platform: %s", platform)
                continue

            try:
                connector = connector_cls()
                config = json.loads(integration.config_json) if integration.config_json else {}
                if not connector.authenticate(config):
                    logger.warning("Connector auth failed for %s", platform)
                    continue

                items: List[DigestItem] = connector.fetch_updates()
                for item in items:
                    state.connector_items.append({
                        "source": item.source,
                        "subject": item.title,
                        "body": item.body,
                        "due_date": item.due_date,
                        "tags": item.tags,
                        "timestamp": item.timestamp,
                    })
                logger.info("Connector %s returned %d items", platform, len(items))
            except Exception as exc:
                logger.error("Connector %s failed: %s", platform, exc)

    return state


@_state_node
def parse_pdfs_node(state: DigestState) -> DigestState:
    logger.info("Loading PDF texts for digest workflow")
    db = get_db()
    with db.session_scope() as session:
        docs: Sequence[Document] = session.query(Document).order_by(Document.created_at.desc()).limit(10).all()
        state.pdf_texts = [doc.text for doc in docs]
    return state


@_state_node
def rag_retrieve_node(state: DigestState) -> DigestState:
    logger.info("Running RAG retrieval")
    query = state.user_context.get("query") or "latest school updates"
    try:
        state.retrieved_context = rag_store.retrieve(query)
    except Exception as exc:
        logger.warning("RAG retrieval failed; continuing digest without RAG context: %s", exc)
        state.retrieved_context = []
    return state


@_state_node
def extract_actions_node(state: DigestState) -> DigestState:
    logger.info("Extracting actions and due dates")
    items: List[Dict[str, Any]] = []

    # Gmail messages — prefer per-child groups if available
    if state.gmail_by_child:
        for group in state.gmail_by_child:
            child_id = group.get("child_id")
            child_name = group.get("child_name", "General")
            for message in group.get("messages", []):
                snippet = message.get("snippet") or ""
                subject = _extract_header(message, "Subject")
                body = snippet
                due_date = _extract_first_date(body)
                tags = _extract_tags(body)
                if subject or body:
                    items.append({
                        "source": "gmail",
                        "subject": subject,
                        "body": body,
                        "due_date": due_date,
                        "tags": tags,
                        "child_id": child_id,
                        "child_name": child_name,
                    })
    else:
        for message in state.gmail_messages:
            snippet = message.get("snippet") or ""
            subject = _extract_header(message, "Subject")
            body = snippet
            due_date = _extract_first_date(body)
            tags = _extract_tags(body)
            if subject or body:
                items.append({
                    "source": "gmail",
                    "subject": subject,
                    "body": body,
                    "due_date": due_date,
                    "tags": tags,
                })

    # Connector items (already structured)
    items.extend(state.connector_items)

    # PDF texts
    for pdf_text in state.pdf_texts:
        due_date = _extract_first_date(pdf_text)
        tags = _extract_tags(pdf_text)
        summary = pdf_text[:280]
        items.append({
            "source": "pdf",
            "subject": "Document Update",
            "body": summary,
            "due_date": due_date,
            "tags": tags,
        })

    # RAG context
    for context_chunk in state.retrieved_context:
        text = context_chunk.get("text", "")
        if not text:
            continue
        items.append({
            "source": "rag",
            "subject": "Contextual Insight",
            "body": text[:280],
            "due_date": _extract_first_date(text),
            "tags": _extract_tags(text),
        })

    state.extracted_items = items
    return state


@_state_node
def fetch_school_sources_node(state: DigestState) -> DigestState:
    """Pull calendar events, announcements, and docs from verified school sources."""
    user_id = state.user_context.get("user_id")
    if not user_id:
        return state

    db = get_db()
    with db.session_scope() as session:
        children = session.query(Child).filter(Child.user_id == user_id).all()
        for c in children:
            state.children_map[c.id] = c.name

        sources = session.query(SchoolSource).filter(
            SchoolSource.user_id == user_id,
            SchoolSource.status.in_(("linked", "verified")),
        ).all()

        for source in sources:
            cid = source.child_id
            # Pull calendar events from Documents with matching child_id
            cal_docs = session.query(Document).filter(
                Document.filename.like("calendar_%"),
            ).order_by(Document.created_at.desc()).limit(20).all()

            for doc in cal_docs:
                meta = _parse_metadata(doc)
                if meta.get("child_id") != cid:
                    continue
                events = meta.get("events", [])
                if events:
                    state.school_events_by_child.setdefault(cid, []).extend(events)

            # Pull announcements from website docs
            web_docs = session.query(Document).filter(
                Document.filename.like("website_%"),
            ).order_by(Document.created_at.desc()).limit(20).all()

            for doc in web_docs:
                meta = _parse_metadata(doc)
                if meta.get("child_id") != cid:
                    continue
                announcements = meta.get("announcements", [])
                if announcements:
                    state.announcements_by_child.setdefault(cid, []).extend(announcements)

            # Pull school docs extractions
            school_docs = session.query(Document).filter(
                Document.filename.like("doc_%"),
            ).order_by(Document.created_at.desc()).limit(20).all()

            for doc in school_docs:
                meta = _parse_metadata(doc)
                if meta.get("child_id") != cid:
                    continue
                extracted = meta.get("extracted", {})
                if extracted:
                    state.school_docs_by_child.setdefault(cid, []).append(extracted)

    logger.info(
        "School sources: events for %d children, announcements for %d children, docs for %d children",
        len(state.school_events_by_child),
        len(state.announcements_by_child),
        len(state.school_docs_by_child),
    )
    return state


@_state_node
def classify_emails_node(state: DigestState) -> DigestState:
    """Run email classifier on Gmail messages to tag platform and extract events."""
    user_id = state.user_context.get("user_id")
    if not state.gmail_by_child and not state.gmail_messages:
        return state

    from services.email_classifier import classify_emails_batch
    from services import gmail as gmail_svc

    child_names = list(state.children_map.values())
    # Collect school names from context
    school_names = []
    db = get_db()
    if user_id:
        with db.session_scope() as session:
            children = session.query(Child).filter(Child.user_id == user_id).all()
            school_names = [c.school_name for c in children if c.school_name]

    # Build email list from gmail_by_child or flat gmail_messages
    email_batch = []
    if state.gmail_by_child:
        for group in state.gmail_by_child:
            for msg in group.get("messages", []):
                email_batch.append({
                    "sender": gmail_svc.extract_from_email(msg),
                    "subject": gmail_svc.extract_header(msg, "Subject"),
                    "snippet": msg.get("snippet", ""),
                    "child_id": group.get("child_id"),
                    "child_name": group.get("child_name"),
                })
    else:
        for msg in state.gmail_messages:
            email_batch.append({
                "sender": gmail_svc.extract_from_email(msg),
                "subject": gmail_svc.extract_header(msg, "Subject"),
                "snippet": msg.get("snippet", ""),
            })

    if email_batch:
        # Classify without LLM for speed (deterministic pass only in digest pipeline)
        state.classified_emails = classify_emails_batch(
            email_batch,
            child_names=child_names,
            school_names=school_names,
            use_llm=False,
        )
        logger.info("Classified %d emails", len(state.classified_emails))

    return state


@_state_node
def compose_digest_node(state: DigestState) -> DigestState:
    """Compose per-child grouped digest using versioned prompt.

    Falls back to legacy summarize_digest if no children are configured.
    """
    logger.info("Composing digest with LLM summarization (%d items)", len(state.extracted_items))

    email = state.user_context.get("email")

    # Check if we have per-child data to use the new prompt
    has_child_context = (
        state.children_map
        and (state.school_events_by_child or state.announcements_by_child
             or state.school_docs_by_child or state.gmail_by_child)
    )

    if has_child_context:
        markdown, usage = _compose_with_child_prompt(state)
    else:
        # Legacy fallback
        user_api_key = None
        user_model = None
        if email:
            db = get_db()
            with db.session_scope() as session:
                openai_integration = (
                    session.query(UserIntegration)
                    .filter(UserIntegration.user.has(email=email))
                    .filter(UserIntegration.platform == "openai")
                    .filter(UserIntegration.status == "connected")
                    .first()
                )
                if openai_integration:
                    config = json.loads(openai_integration.config_json) if openai_integration.config_json else {}
                    user_api_key = config.get("api_key")
                    user_model = config.get("model")

        markdown, usage = summarize_digest(
            state.extracted_items,
            user_api_key=user_api_key,
            user_model=user_model,
        )

    state.digest_markdown = markdown
    state.llm_usage = usage
    return state


def _compose_with_child_prompt(state: DigestState) -> tuple:
    """Compose digest using the per-child grouped prompt template."""
    from datetime import date
    from services.gemini import generate
    from services.prompt_loader import load_prompt

    system_prompt = load_prompt("digest_compose_prompt_v1")

    # Build per-child context
    children_data = []
    for child_id, child_name in sorted(state.children_map.items(), key=lambda x: x[1]):
        # Calendar events
        cal_events = state.school_events_by_child.get(child_id, [])
        # Announcements
        announcements = state.announcements_by_child.get(child_id, [])
        # School docs facts
        docs_facts = []
        for doc_extract in state.school_docs_by_child.get(child_id, []):
            docs_facts.extend(doc_extract.get("facts", []))
            docs_facts.extend(doc_extract.get("actions", []))
        # Recent emails for this child
        child_emails = []
        for ce in state.classified_emails:
            ce_email = ce.get("email", {})
            if ce.get("child_match") == child_name:
                child_emails.append({
                    "subject": ce_email.get("subject"),
                    "platform": ce.get("platform"),
                    "urgency": ce.get("extracted", {}).get("urgency", "low"),
                    "is_actionable": ce.get("extracted", {}).get("is_actionable", False),
                })
        # Also include Gmail items from extracted_items
        for item in state.extracted_items:
            if item.get("child_id") == child_id:
                child_emails.append({
                    "subject": item.get("subject"),
                    "platform": "gmail",
                    "urgency": "medium" if "action" in item.get("tags", []) else "low",
                    "is_actionable": "action" in item.get("tags", []),
                })

        children_data.append({
            "name": child_name,
            "context": {
                "calendar_events": cal_events[:20],
                "recent_emails": child_emails[:15],
                "school_docs_facts": docs_facts[:15],
                "announcements": announcements[:10],
            },
        })

    # Also add unmatched items as "General" section
    general_items = []
    for item in state.extracted_items:
        if not item.get("child_id") and not item.get("child_name"):
            general_items.append({
                "subject": item.get("subject"),
                "body": item.get("body", "")[:200],
                "source": item.get("source"),
            })
    if general_items:
        children_data.append({
            "name": "General",
            "context": {
                "calendar_events": [],
                "recent_emails": general_items[:10],
                "school_docs_facts": [],
                "announcements": [],
            },
        })

    user_prompt = json.dumps({
        "date": date.today().isoformat(),
        "children": children_data,
    }, default=str)

    result = generate(prompt=user_prompt, system_instruction=system_prompt)

    usage = None
    if result.model != "none":
        usage = {
            "model": result.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "estimated_cost_usd": result.estimated_cost_usd,
        }

    return result.text or "", usage


# --- Graph wiring ---

graph = StateGraph(DigestStateDict)
graph.add_node("fetch_gmail_node", fetch_gmail_node)
graph.add_node("fetch_connectors_node", fetch_connectors_node)
graph.add_node("fetch_school_sources_node", fetch_school_sources_node)
graph.add_node("classify_emails_node", classify_emails_node)
graph.add_node("parse_pdfs_node", parse_pdfs_node)
graph.add_node("rag_retrieve_node", rag_retrieve_node)
graph.add_node("extract_actions_node", extract_actions_node)
graph.add_node("compose_digest_node", compose_digest_node)

graph.set_entry_point("fetch_gmail_node")
graph.add_edge("fetch_gmail_node", "fetch_connectors_node")
graph.add_edge("fetch_connectors_node", "fetch_school_sources_node")
graph.add_edge("fetch_school_sources_node", "classify_emails_node")
graph.add_edge("classify_emails_node", "parse_pdfs_node")
graph.add_edge("parse_pdfs_node", "rag_retrieve_node")
graph.add_edge("rag_retrieve_node", "extract_actions_node")
graph.add_edge("extract_actions_node", "compose_digest_node")
graph.add_edge("compose_digest_node", END)

compiled_graph = graph.compile()


def run_digest(payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute the LangGraph workflow and return resulting payload."""

    initial_state: DigestStateDict = _default_state(payload)
    result_state: DigestStateDict = compiled_graph.invoke(initial_state)
    result = {
        "digest_markdown": result_state.get("digest_markdown", ""),
        "items_json": json.dumps(result_state.get("extracted_items", []), default=str),
        "raw_json": json.dumps(
            {
                "gmail_messages": result_state.get("gmail_messages", []),
                "connector_items": result_state.get("connector_items", []),
                "retrieved_context": result_state.get("retrieved_context", []),
                "school_events_by_child": result_state.get("school_events_by_child", {}),
                "classified_emails": result_state.get("classified_emails", []),
            },
            default=str,
        ),
        "source": payload.get("source", "multi") if payload else "multi",
    }
    if result_state.get("llm_usage"):
        result["llm_usage"] = result_state["llm_usage"]
    return result


# --- Helpers ---

def _parse_metadata(doc: Document) -> Dict[str, Any]:
    """Parse metadata_json from a Document, handling missing attr gracefully."""
    if not hasattr(doc, "metadata_json") or not doc.metadata_json:
        return {}
    try:
        return json.loads(doc.metadata_json)
    except (json.JSONDecodeError, TypeError):
        return {}

def _extract_header(message: Dict[str, Any], header_name: str) -> str:
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    for header in headers:
        if header.get("name") == header_name:
            return header.get("value", "")
    return ""


def _extract_tags(text: str) -> List[str]:
    lowered = text.lower()
    tags = []
    if any(keyword in lowered for keyword in ("due", "deadline", "submit")):
        tags.append("action")
    if any(keyword in lowered for keyword in ("payment", "fee")):
        tags.append("finance")
    if any(keyword in lowered for keyword in ("event", "field trip", "performance")):
        tags.append("event")
    return tags or ["general"]


def _extract_first_date(text: str) -> Optional[str]:
    tokens = text.split()
    for token in tokens:
        try:
            parsed = date_parser.parse(token, fuzzy=False)
            if parsed.year >= datetime.utcnow().year - 1:
                return parsed.date().isoformat()
        except (ValueError, OverflowError):
            continue
    return None
