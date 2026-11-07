from datetime import date

import pytest

from src.retrieval.knowledge import KnowledgeChunk, KnowledgeStore, validate_citation


def chunk(chunk_id, *, review_status="reviewed", jurisdiction="CN-mainland",
          effective_from="2021-01-01", effective_to=None, keywords=("Price",)):
    return KnowledgeChunk.from_dict({
        "chunk_id": chunk_id, "source": "fixture", "title": chunk_id, "text": "The price is agreed by both parties.",
        "url": "https://example.invalid/knowledge", "jurisdiction": jurisdiction,
        "effective_from": effective_from, "effective_to": effective_to,
        "source_version": "test-v1", "retrieved_at": "2026-10-21", "review_status": review_status,
        "keywords": list(keywords),
    })


def test_review_and_applicability_filter_precedes_scoring():
    store = KnowledgeStore([
        chunk("approved"), chunk("pending", review_status="pending"),
        chunk("foreign", jurisdiction="US"),
        chunk("future", effective_from="2027-01-01"),
        chunk("expired", effective_to="2026-01-01"),
    ])
    result = store.retrieve("Price", jurisdiction="CN-mainland", as_of=date(2026, 10, 20))
    assert [item.chunk_id for item in result.chunks] == ["approved"]
    assert result.eligible_count == 1


def test_no_keyword_match_and_stable_tie_order():
    store = KnowledgeStore([chunk("b"), chunk("a")])
    assert store.retrieve("Payment", jurisdiction="CN-mainland", as_of=date(2026, 10, 20)).chunks == ()
    matched = store.retrieve("Price", jurisdiction="CN-mainland", as_of=date(2026, 10, 20))
    assert [item.chunk_id for item in matched.chunks] == ["a", "b"]


def test_citation_must_match_current_retrieval_and_quote():
    store = KnowledgeStore([chunk("a"), chunk("b", keywords=("delivery",))])
    result = store.retrieve("Price", jurisdiction="CN-mainland", as_of=date(2026, 10, 20))
    citation = validate_citation({"chunk_id": "a", "source_version": "test-v1", "quote": "price"}, result)
    assert citation["url"] == "https://example.invalid/knowledge"
    for bad in ({"chunk_id": "b", "source_version": "test-v1", "quote": "price"},
                {"chunk_id": "a", "source_version": "test-v1", "quote": "absent quotation"},
                {"chunk_id": "a", "source_version": "old", "quote": "price"}):
        with pytest.raises(ValueError):
            validate_citation(bad, result)
