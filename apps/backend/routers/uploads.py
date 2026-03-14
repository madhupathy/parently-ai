"""Upload-related routers."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from config import get_settings
from dependencies import get_current_user
from services.pdf import extract_text_from_pdf
from storage import rag_store
from storage.models import User

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()


@router.post("/pdf")
async def upload_pdf(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
) -> dict[str, object]:
    if file.content_type not in {"application/pdf"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "invalid_type"})
    target_folder = settings.pdf_folder
    target_folder.mkdir(parents=True, exist_ok=True)
    file_path = target_folder / file.filename
    data = await file.read()
    file_path.write_bytes(data)
    text = extract_text_from_pdf(file_path)
    doc_id = rag_store.add_document(file.filename, file.content_type, text)
    return {"ok": True, "document_id": doc_id}


@router.get("/list")
def list_uploads(current_user: User = Depends(get_current_user)) -> dict[str, object]:
    docs = rag_store.list_documents()
    return {"ok": True, "documents": docs}
