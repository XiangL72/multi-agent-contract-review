"""English workflow boundaries and original-source citation behavior."""
import asyncio
from datetime import date
from pathlib import Path
import pytest
from src.demo.fake_llm import install_demo_model
from src.pipeline.runner import run_review
from src.pipeline.state import ReviewStatus
from src.retrieval.knowledge import KnowledgeStore, validate_citation

ROOT = Path(__file__).resolve().parents[2]

@pytest.fixture
def offline_model(monkeypatch):
    from src.agents import clause_extraction, risk_identification, compliance_check, suggestion
    from src.demo.fake_llm import DemoLLM
    fake = DemoLLM()
    for module in (clause_extraction, risk_identification, compliance_check, suggestion):
        monkeypatch.setattr(module, "get_llm", lambda: fake)


def test_complete_english_purchase_has_no_missing_information(offline_model):
    text = (ROOT / "examples/purchase-complete.txt").read_text()
    result = asyncio.run(run_review(text))
    assert result.status == ReviewStatus.SUCCESS
    assert result.jurisdiction == "CN-mainland"
    assert result.contract_type == "purchase_contract"
    assert result.missing_clauses == []
    assert result.clauses[0].content == text


def test_missing_price_preserves_original_citation_and_english_gloss(offline_model):
    text = (ROOT / "examples/purchase-missing-price.txt").read_text()
    result = asyncio.run(run_review(text))
    assert result.status == ReviewStatus.SUCCESS
    assert "Price" in result.missing_clauses
    assert any(f.risk_type == "unlimited_liability" for f in result.risk_findings)
    finding = result.compliance_findings[0]
    assert text[finding.evidence.start:finding.evidence.end] == finding.evidence.quote
    citation = finding.knowledge_citations[0]
    original = next(c for c in KnowledgeStore.load().chunks if c.chunk_id == citation["chunk_id"])
    assert citation["quote"] == original.text
    assert citation["english_gloss"] == original.english_gloss
    assert citation["english_gloss_status"] == "unreviewed_translation"
    assert result.diagnostics[-1]["calls_used"] == 4
    assert any(s.original_text == text for s in result.suggestions if s.kind == "revision")


def test_english_gloss_is_not_accepted_as_original_evidence():
    retrieved = KnowledgeStore.load().retrieve("PRICE not agreed", jurisdiction="CN-mainland", as_of=date(2026, 10, 20))
    chunk = next(c for c in retrieved.chunks if c.chunk_id == "civil-code-510")
    with pytest.raises(ValueError):
        validate_citation({"chunk_id": chunk.chunk_id, "source_version": chunk.source_version, "quote": chunk.english_gloss}, retrieved)


def test_retrieval_uses_word_boundaries_and_does_not_select_foreign_law():
    store = KnowledgeStore.load()
    assert not store.retrieve("priceless", jurisdiction="CN-mainland", as_of=date(2026, 10, 20)).chunks
    assert not store.retrieve("purchase price", jurisdiction="CA", as_of=date(2026, 10, 20)).chunks


def test_case_insensitive_price_and_quantity():
    from src.agents.compliance_check import ComplianceCheckAgent
    from src.pipeline.state import Clause
    clause = Clause(title="Payment", content="The PRICE is RMB 1,000.50 for 10 UNITS.")
    missing = ComplianceCheckAgent()._check_missing_clauses([clause], "purchase_contract")
    assert "Price" not in missing and "Quantity" not in missing
