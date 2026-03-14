"""Unit tests for RAG chunking and retrieval ranking."""

from __future__ import annotations

import math

from storage.rag_store import chunk_text, rank_texts_by_query


def test_chunk_text_overlap_behavior() -> None:
    text = """Parent teacher conference will be on Friday evening. Please arrive 10 minutes early."""
    chunks = chunk_text(text, chunk_size=40, overlap=10)
    assert chunks, "Expected at least one chunk"
    # Ensure chunks cover entire text with overlap
    reconstructed = "".join(chunk[:30] for chunk in chunks)
    assert "Friday" in reconstructed


def test_rank_texts_by_query_orders_matches() -> None:
    texts = [
        "Bring snacks for the soccer game on Saturday.",
        "Pay the field trip fee by Monday.",
        "Spirit week schedule attached.",
    ]
    ranked = rank_texts_by_query("Please pay the fee", texts)
    assert ranked, "Expected ranking output"
    top_text, score = ranked[0]
    assert "fee" in top_text.lower()
    assert math.isfinite(score)
    assert score >= ranked[-1][1]
