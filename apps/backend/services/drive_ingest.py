"""Google Drive folder ingestion — list and process school docs from Drive.

Reuses the existing gdrive connector for authentication, lists files from
a connected Drive folder, downloads PDFs, and processes them through
the school_docs_extract pipeline.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from storage import get_db
from storage.models import Child, UserIntegration

logger = logging.getLogger(__name__)


def ingest_drive_docs_for_user(user_id: int) -> Dict[str, Any]:
    """Ingest school docs from connected Google Drive for all children.

    Returns summary of ingestion results.
    """
    db = get_db()
    results: Dict[str, Any] = {
        "files_found": 0,
        "files_processed": 0,
        "errors": [],
    }

    # Check for Drive integration
    with db.session_scope() as session:
        drive_integration = session.query(UserIntegration).filter(
            UserIntegration.user_id == user_id,
            UserIntegration.platform == "gdrive",
            UserIntegration.status == "connected",
        ).first()

        if not drive_integration:
            logger.debug("No connected Drive integration for user %d", user_id)
            return results

        config = json.loads(drive_integration.config_json) if drive_integration.config_json else {}
        folder_id = config.get("folder_id")

        children = session.query(Child).filter(Child.user_id == user_id).all()
        children_data = [
            {
                "id": c.id,
                "name": c.name,
                "school_name": c.school_name or "School",
            }
            for c in children
        ]

    if not folder_id:
        logger.debug("No Drive folder_id configured for user %d", user_id)
        return results

    # List files from Drive folder
    files = _list_drive_files(config, folder_id)
    results["files_found"] = len(files)

    if not files:
        return results

    # Process each PDF file
    from services.school_docs_extract import extract_and_store

    for file_info in files:
        mime = file_info.get("mimeType", "")
        if "pdf" not in mime.lower() and not file_info.get("name", "").lower().endswith(".pdf"):
            continue

        try:
            text = _download_file_text(config, file_info["id"])
            if not text:
                continue

            # Try to match to a child by school name in filename
            child_id = None
            child_name = None
            school_name = "School"
            fname_lower = file_info.get("name", "").lower()
            for cd in children_data:
                if cd["school_name"].lower() in fname_lower or cd["name"].lower() in fname_lower:
                    child_id = cd["id"]
                    child_name = cd["name"]
                    school_name = cd["school_name"]
                    break

            if not child_id and children_data:
                # Default to first child
                child_id = children_data[0]["id"]
                child_name = children_data[0]["name"]
                school_name = children_data[0]["school_name"]

            extract_and_store(
                text_content=text,
                filename=file_info.get("name", "drive_doc.pdf"),
                school_name=school_name,
                child_name=child_name,
                child_id=child_id,
                source_type="drive_doc",
            )
            results["files_processed"] += 1
        except Exception as exc:
            logger.warning("Drive file processing failed for %s: %s", file_info.get("name"), exc)
            results["errors"].append({"file": file_info.get("name"), "error": str(exc)})

    logger.info("Drive ingest for user %d: %s", user_id, results)
    return results


def _list_drive_files(config: Dict[str, Any], folder_id: str) -> List[Dict[str, Any]]:
    """List files in a Google Drive folder using the API."""
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials

        creds_data = config.get("credentials")
        if not creds_data:
            return []

        creds = Credentials(
            token=creds_data.get("token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
        )

        service = build("drive", "v3", credentials=creds)
        query = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(
            q=query,
            fields="files(id, name, mimeType, modifiedTime)",
            pageSize=50,
        ).execute()

        return response.get("files", [])
    except Exception as exc:
        logger.warning("Drive listing failed: %s", exc)
        return []


def _download_file_text(config: Dict[str, Any], file_id: str) -> Optional[str]:
    """Download a file from Drive and extract text (PDF only)."""
    try:
        from googleapiclient.discovery import build
        from google.oauth2.credentials import Credentials
        import io
        from pypdf import PdfReader

        creds_data = config.get("credentials")
        if not creds_data:
            return None

        creds = Credentials(
            token=creds_data.get("token"),
            refresh_token=creds_data.get("refresh_token"),
            token_uri=creds_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=creds_data.get("client_id"),
            client_secret=creds_data.get("client_secret"),
        )

        service = build("drive", "v3", credentials=creds)
        content = service.files().get_media(fileId=file_id).execute()

        reader = PdfReader(io.BytesIO(content))
        text_parts = []
        for page in reader.pages:
            text_parts.append(page.extract_text() or "")
        return "\n".join(text_parts)
    except Exception as exc:
        logger.warning("Drive file download failed for %s: %s", file_id, exc)
        return None
