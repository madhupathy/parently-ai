"""RAG store for Parently — pgvector on Postgres, in-memory fallback on SQLite."""

from __future__ import annotations

import json
import logging
import math
from typing import Dict, List, Optional, Sequence, Tuple

import httpx
from openai import OpenAI

from config import get_settings
from .database import get_db
from .models import Document, Embedding

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Chunk text with configurable overlap."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    cleaned = text.replace("\r", "")
    chunks: List[str] = []
    start = 0
    step = max(chunk_size - overlap, 1)
    while start < len(cleaned):
        end = min(len(cleaned), start + chunk_size)
        chunk = cleaned[start:end].strip()
        if chunk:
            chunks.append(chunk)
        start += step
    return chunks or ([cleaned] if cleaned else [])


def cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Compute cosine similarity between two vectors."""

    if not vec_a or not vec_b:
        return 0.0
    if len(vec_a) != len(vec_b):
        raise ValueError("Vectors must be same length")
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _cheap_embedding(text: str, dim: int = 256) -> List[float]:
    vec = [0.0] * dim
    for idx, ch in enumerate(text):
        vec[idx % dim] += (ord(ch) % 31) / 31.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    settings = get_settings()
    if settings.gemini_api_key:
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.gemini_api_key)
            result = genai.embed_content(
                model="models/text-embedding-004",
                content=list(texts),
            )
            return result["embedding"]
        except Exception as exc:
            logger.warning("Falling back from Gemini embeddings: %s", exc)
    if settings.openai_api_key:
        try:
            client = OpenAI(api_key=settings.openai_api_key)
            response = client.embeddings.create(model="text-embedding-3-small", input=list(texts))
            return [record.embedding for record in response.data]
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Falling back from OpenAI embeddings: %s", exc)
    return [_cheap_embedding(text) for text in texts]


def add_document(filename: str, mime: str, text: str) -> int:
    """Store a document with chunk metadata and embeddings in the Embedding table."""

    settings = get_settings()
    db = get_db()
    chunks = chunk_text(text, settings.rag_chunk_size, settings.rag_chunk_overlap)
    embeddings = embed_texts(chunks) if chunks else []
    with db.session_scope() as session:
        document = Document(
            filename=filename,
            mime=mime,
            text=text,
            chunks_json=json.dumps(chunks),
            embeddings_json=json.dumps(embeddings),
        )
        session.add(document)
        session.flush()

        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            row = Embedding(
                document_id=document.id,
                chunk_index=idx,
                chunk_text=chunk,
                embedding_json=json.dumps(emb),
            )
            session.add(row)

        return document.id


def list_documents() -> List[Dict[str, str]]:
    db = get_db()
    with db.session_scope() as session:
        rows = session.query(Document).order_by(Document.created_at.desc()).all()
        return [
            {
                "id": row.id,
                "filename": row.filename,
                "mime": row.mime,
                "created_at": row.created_at.isoformat(),
            }
            for row in rows
        ]


def retrieve(query: str, top_k: Optional[int] = None) -> List[Dict[str, object]]:
    settings = get_settings()
    limit = top_k or settings.rag_top_k
    db = get_db()
    query_embed = embed_texts([query])[0]

    with db.session_scope() as session:
        emb_rows = session.query(Embedding).all()
        if not emb_rows:
            return []

        scored: List[Tuple[float, str, int]] = []
        for row in emb_rows:
            row_vec = row.get_embedding()
            if not row_vec:
                continue
            sim = cosine_similarity(query_embed, row_vec)
            scored.append((sim, row.chunk_text, row.document_id))

    scored.sort(key=lambda item: item[0], reverse=True)
    top = scored[:limit]
    return [
        {"similarity": sim, "text": text, "document_id": doc_id}
        for sim, text, doc_id in top
    ]


def rank_texts_by_query(query: str, texts: Sequence[str]) -> List[Tuple[str, float]]:
    """Utility used in tests to validate ranking logic."""

    if not texts:
        return []
    embeddings = embed_texts([*texts, query])
    query_vec = embeddings[-1]
    scores = [cosine_similarity(vec, query_vec) for vec in embeddings[:-1]]
    combined = list(zip(texts, scores))
    combined.sort(key=lambda item: item[1], reverse=True)
    return combined
