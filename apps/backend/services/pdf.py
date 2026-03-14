"""PDF utilities."""

from __future__ import annotations

from pathlib import Path
from typing import List

from pypdf import PdfReader


def extract_text_from_pdf(file_path: Path) -> str:
    """Extract raw text from the given PDF path."""

    reader = PdfReader(str(file_path))
    parts: List[str] = []
    for page in reader.pages:
        text = page.extract_text() or ""
        parts.append(text)
    return "\n".join(parts).strip()
