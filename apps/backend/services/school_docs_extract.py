"""School docs extraction — process PDFs/uploaded docs with LLM.

Extracts structured facts, actions, and dates from school documents
(handbooks, schedules, policies) and stores them as Document metadata.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from storage import get_db, rag_store
from storage.models import Document

logger = logging.getLogger(__name__)


def extract_and_store(
    text_content: str,
    filename: str,
    school_name: str,
    child_name: Optional[str] = None,
    child_id: Optional[int] = None,
    source_type: str = "uploaded_doc",
) -> Dict[str, Any]:
    """Process a document's text with LLM and store extracted info.

    Args:
        text_content: Extracted text from the PDF/document.
        filename: Original filename.
        school_name: School name for context.
        child_name: Child name (may be None).
        child_id: Child ID (may be None).
        source_type: "uploaded_doc" or "drive_doc".

    Returns:
        Dict with extraction results and document ID.
    """
    from services.gemini import generate
    from services.prompt_loader import load_prompt

    # Truncate long docs for LLM
    truncated = text_content[:10000]

    system_prompt = load_prompt("school_docs_extract_prompt_v1")
    user_prompt = json.dumps({
        "school_name": school_name,
        "child_name": child_name,
        "filename": filename,
        "text_content": truncated,
    })

    result = generate(prompt=user_prompt, system_instruction=system_prompt)

    extracted = {"facts": [], "actions": [], "dates": []}
    if result.text:
        extracted = _parse_extraction(result.text)

    # Store document via RAG store
    content_hash = hashlib.sha256(text_content.encode()).hexdigest()[:12]
    rag_filename = f"doc_{source_type}_{content_hash}.pdf"

    # Dedup check
    db = get_db()
    with db.session_scope() as session:
        existing = session.query(Document).filter(
            Document.filename == rag_filename
        ).first()
        if existing:
            existing.text = text_content
            if hasattr(existing, "metadata_json"):
                existing.metadata_json = json.dumps({
                    "source_type": source_type,
                    "child_id": child_id,
                    "school_name": school_name,
                    "original_filename": filename,
                    "extracted": extracted,
                    "updated_at": datetime.utcnow().isoformat(),
                })
            doc_id = existing.id
        else:
            doc_id = rag_store.add_document(rag_filename, "application/pdf", text_content)
            with db.session_scope() as session:
                doc = session.query(Document).filter(Document.id == doc_id).first()
                if doc and hasattr(doc, "metadata_json"):
                    doc.metadata_json = json.dumps({
                        "source_type": source_type,
                        "child_id": child_id,
                        "school_name": school_name,
                        "original_filename": filename,
                        "extracted": extracted,
                    })

    logger.info(
        "Extracted from '%s': %d facts, %d actions, %d dates",
        filename, len(extracted["facts"]), len(extracted["actions"]), len(extracted["dates"]),
    )

    return {
        "document_id": doc_id,
        "facts": extracted["facts"],
        "actions": extracted["actions"],
        "dates": extracted["dates"],
    }


def extract_from_pdf_path(
    pdf_path: str,
    school_name: str,
    child_name: Optional[str] = None,
    child_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Extract from a local PDF file path."""
    from pypdf import PdfReader
    import os

    reader = PdfReader(pdf_path)
    text_parts = []
    for page in reader.pages:
        text_parts.append(page.extract_text() or "")
    text = "\n".join(text_parts)

    filename = os.path.basename(pdf_path)
    return extract_and_store(
        text_content=text,
        filename=filename,
        school_name=school_name,
        child_name=child_name,
        child_id=child_id,
        source_type="uploaded_doc",
    )


def _parse_extraction(raw_text: str) -> Dict[str, List[Dict[str, Any]]]:
    """Parse LLM JSON response into facts/actions/dates."""
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
                return {"facts": [], "actions": [], "dates": []}
        else:
            return {"facts": [], "actions": [], "dates": []}

    return {
        "facts": data.get("facts", []),
        "actions": data.get("actions", []),
        "dates": data.get("dates", []),
    }
