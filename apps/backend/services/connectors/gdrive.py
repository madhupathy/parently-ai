"""Google Drive connector — syncs documents from a shared folder."""

from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .base import BaseConnector, DigestItem

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

SUPPORTED_MIME = {
    "application/pdf",
    "application/vnd.google-apps.document",
    "text/plain",
}


class GoogleDriveConnector(BaseConnector):
    """Fetch documents from a Google Drive folder using OAuth tokens."""

    platform = "gdrive"

    def __init__(self) -> None:
        self._credentials: Optional[Credentials] = None
        self._folder_id: Optional[str] = None
        self._service: Optional[Any] = None

    def authenticate(self, credentials: Dict[str, Any]) -> bool:
        """Build Drive service from OAuth token dict and folder ID."""
        self._folder_id = credentials.get("folder_id")
        token_info = credentials.get("token")
        if not self._folder_id or not token_info:
            logger.warning("Google Drive connector: missing folder_id or token")
            return False

        try:
            creds = Credentials.from_authorized_user_info(token_info, scopes=SCOPES)
            if not creds.valid and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            self._credentials = creds
            self._service = build("drive", "v3", credentials=creds)
            # Quick validation — list folder
            self._service.files().list(
                q=f"'{self._folder_id}' in parents",
                pageSize=1,
                fields="files(id)",
            ).execute()
            return True
        except Exception as exc:
            logger.error("Google Drive auth failed: %s", exc)
            return False

    def fetch_updates(self, since: Optional[datetime] = None) -> List[DigestItem]:
        """List files in the configured Drive folder and return as digest items."""
        if not self._service or not self._folder_id:
            logger.warning("Google Drive connector not authenticated")
            return []

        try:
            query = f"'{self._folder_id}' in parents and trashed = false"
            if since:
                query += f" and modifiedTime > '{since.isoformat()}Z'"

            response = self._service.files().list(
                q=query,
                pageSize=20,
                fields="files(id, name, mimeType, modifiedTime, description)",
                orderBy="modifiedTime desc",
            ).execute()

            items: List[DigestItem] = []
            for f in response.get("files", []):
                name = f.get("name", "Untitled")
                mime = f.get("mimeType", "")
                modified = f.get("modifiedTime", "")
                desc = f.get("description", "")

                body = desc or f"Document: {name}"
                # Try to extract text from Google Docs
                if mime == "application/vnd.google-apps.document":
                    body = self._export_doc_text(f["id"]) or body
                elif mime == "application/pdf":
                    body = self._download_pdf_text(f["id"]) or body

                items.append(DigestItem(
                    source="gdrive",
                    title=name,
                    body=body[:500],
                    due_date=modified[:10] if modified else None,
                    tags=["document"],
                    timestamp=modified,
                    raw=f,
                ))
            logger.info("Google Drive: fetched %d items", len(items))
            return items
        except Exception as exc:
            logger.error("Google Drive fetch failed: %s", exc)
            return []

    def _export_doc_text(self, file_id: str) -> Optional[str]:
        """Export a Google Doc as plain text."""
        try:
            content = self._service.files().export(
                fileId=file_id, mimeType="text/plain"
            ).execute()
            if isinstance(content, bytes):
                return content.decode("utf-8", errors="replace")[:2000]
            return str(content)[:2000]
        except Exception as exc:
            logger.debug("Failed to export doc %s: %s", file_id, exc)
            return None

    def _download_pdf_text(self, file_id: str) -> Optional[str]:
        """Download a PDF and extract text."""
        try:
            from services.pdf import extract_text_from_pdf
            import tempfile
            from pathlib import Path

            request = self._service.files().get_media(fileId=file_id)
            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            buf.seek(0)

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(buf.read())
                tmp_path = Path(tmp.name)
            text = extract_text_from_pdf(tmp_path)
            tmp_path.unlink(missing_ok=True)
            return text[:2000]
        except Exception as exc:
            logger.debug("Failed to extract PDF %s: %s", file_id, exc)
            return None
