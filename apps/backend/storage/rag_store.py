"""RAG store for Parently — pgvector on Postgres, in-memory fallback on SQLite."""

from __future__ import annotations

import json
import logging
import math
import re
from typing import Dict, List, Optional, Sequence, Tuple

from openai import OpenAI
from sqlalchemy import text as sql_text

from config import get_settings
from .database import get_db
from .models import Document, DocumentChunk, Embedding

logger = logging.getLogger(__name__)

ACTIVE_EMBEDDING_PROVIDER = "gemini"
ACTIVE_EMBEDDING_MODEL = "gemini-embedding-001"
DEFAULT_EMBEDDING_DIMENSION = 1536
FALLBACK_EMBEDDING_PROVIDER = "deterministic-fallback"
FALLBACK_EMBEDDING_MODEL = "cheap-hash-v1"


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


def _cheap_embedding(text: str, dim: int = DEFAULT_EMBEDDING_DIMENSION) -> List[float]:
    # Deterministic token hashing so lexical overlap ranks meaningfully in fallback mode.
    vec = [0.0] * dim
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    if not tokens:
        tokens = [text.lower()]
    for token in tokens:
        bucket = hash(token) % dim
        vec[bucket] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _embed_texts_with_metadata(
    texts: Sequence[str],
) -> Tuple[List[List[float]], Dict[str, object]]:
    settings = get_settings()
    active_dim = settings.rag_embedding_dimension
    if settings.gemini_api_key:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.gemini_api_key)
            model_name = settings.gemini_embedding_model or ACTIVE_EMBEDDING_MODEL
            logger.info(
                "Using embedding model: provider=gemini model=%s dimension=%d",
                model_name,
                active_dim,
            )
            resp = client.models.embed_content(
                model=model_name,
                contents=list(texts),
                config=types.EmbedContentConfig(output_dimensionality=active_dim),
            )
            vectors: List[List[float]] = []
            embeddings = getattr(resp, "embeddings", None)
            if embeddings is None and isinstance(resp, dict):
                embeddings = resp.get("embeddings")
            if embeddings:
                for emb in embeddings:
                    values = getattr(emb, "values", None)
                    if values is None and isinstance(emb, dict):
                        values = emb.get("values")
                    if values:
                        vectors.append([float(v) for v in values][:active_dim])
            if vectors and len(vectors) == len(texts):
                return vectors, {
                    "embedding_provider": "gemini",
                    "embedding_model": model_name,
                    "embedding_dimension": len(vectors[0]),
                }
            logger.warning("Gemini embedding returned unexpected payload; falling back")
        except Exception as exc:
            logger.warning("Falling back from Gemini embeddings: %s", exc)
    if settings.openai_api_key:
        try:
            client = OpenAI(api_key=settings.openai_api_key)
            openai_model = "text-embedding-3-small"
            logger.info(
                "Using embedding model: provider=openai model=%s dimension=%d",
                openai_model,
                active_dim,
            )
            response = client.embeddings.create(model=openai_model, input=list(texts))
            vectors = [record.embedding[:active_dim] for record in response.data]
            return vectors, {
                "embedding_provider": "openai",
                "embedding_model": openai_model,
                "embedding_dimension": len(vectors[0]) if vectors else active_dim,
            }
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("Falling back from OpenAI embeddings: %s", exc)
    logger.info(
        "Using embedding model: provider=%s model=%s dimension=%d",
        FALLBACK_EMBEDDING_PROVIDER,
        FALLBACK_EMBEDDING_MODEL,
        active_dim,
    )
    vectors = [_cheap_embedding(text, dim=active_dim) for text in texts]
    return vectors, {
        "embedding_provider": FALLBACK_EMBEDDING_PROVIDER,
        "embedding_model": FALLBACK_EMBEDDING_MODEL,
        "embedding_dimension": active_dim,
    }


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    vectors, _ = _embed_texts_with_metadata(texts)
    return vectors


def _vector_literal(vector: Sequence[float]) -> str:
    return "[" + ",".join(f"{x:.8f}" for x in vector) + "]"


def add_document(
    filename: str,
    mime: str,
    text: str,
    *,
    user_id: Optional[int] = None,
    child_id: Optional[int] = None,
    source_type: str = "pdf",
    source_id: Optional[str] = None,
    title: Optional[str] = None,
) -> int:
    """Store a document with chunk and embedding rows."""

    settings = get_settings()
    db = get_db()
    chunks = chunk_text(text, settings.rag_chunk_size, settings.rag_chunk_overlap)
    embeddings, embedding_meta = _embed_texts_with_metadata(chunks) if chunks else ([], {
        "embedding_provider": ACTIVE_EMBEDDING_PROVIDER,
        "embedding_model": settings.gemini_embedding_model,
        "embedding_dimension": settings.rag_embedding_dimension,
    })
    with db.session_scope() as session:
        doc_metadata: Dict[str, object] = {}
        if text:
            doc_metadata = {
                **embedding_meta,
            }
        document = Document(
            user_id=user_id,
            child_id=child_id,
            source_type=source_type,
            source_id=source_id,
            title=title or filename,
            content=text,
            filename=filename,
            mime=mime,
            text=text,
            chunks_json=json.dumps(chunks),
            embeddings_json=json.dumps(embeddings),
            metadata_json=json.dumps(doc_metadata) if doc_metadata else None,
        )
        session.add(document)
        session.flush()

        is_postgres = session.bind and session.bind.dialect.name == "postgresql"

        for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            chunk_row = DocumentChunk(
                document_id=document.id,
                chunk_index=idx,
                chunk_text=chunk,
            )
            session.add(chunk_row)
            session.flush()
            row = Embedding(
                document_id=document.id,
                document_chunk_id=chunk_row.id,
                chunk_index=idx,
                chunk_text=chunk,
                embedding=emb if is_postgres else None,
                embedding_json=None if is_postgres else json.dumps(emb),
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
    query_dim = len(query_embed)
    if query_dim != settings.rag_embedding_dimension:
        logger.warning(
            "Skipping RAG retrieval due to query dimension mismatch (got=%d expected=%d)",
            query_dim,
            settings.rag_embedding_dimension,
        )
        return []

    with db.session_scope() as session:
        is_postgres = session.bind and session.bind.dialect.name == "postgresql"
        if is_postgres:
            vector_literal = _vector_literal(query_embed)
            sql = """
                SELECT
                    1 - (e.embedding <=> CAST(:query_vec AS vector)) AS similarity,
                    dc.chunk_text AS text,
                    dc.document_id AS document_id
                FROM embeddings e
                JOIN document_chunks dc ON dc.id = e.document_chunk_id
                WHERE e.embedding IS NOT NULL
                  AND vector_dims(e.embedding) = :embedding_dim
                ORDER BY e.embedding <=> CAST(:query_vec AS vector)
                LIMIT :k
            """
            try:
                rows = session.execute(
                    sql_text(sql),
                    {
                        "query_vec": vector_literal,
                        "k": limit,
                        "embedding_dim": settings.rag_embedding_dimension,
                    },
                )
            except Exception as exc:
                logger.warning("RAG vector retrieval failed; continuing without context: %s", exc)
                return []
            return [
                {
                    "similarity": float(row.similarity),
                    "text": row.text,
                    "document_id": row.document_id,
                }
                for row in rows
            ]
        emb_rows = session.query(Embedding).all()
        if not emb_rows:
            return []

        scored: List[Tuple[float, str, int]] = []
        for row in emb_rows:
            row_vec = row.get_embedding()
            if not row_vec:
                continue
            if len(row_vec) != query_dim:
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
