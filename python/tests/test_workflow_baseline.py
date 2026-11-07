"""Prove the real graph visits all four stages without a model request."""

import asyncio
import json
import re
from types import SimpleNamespace

from src.agents import clause_extraction, compliance_check, risk_identification, suggestion
from src.pipeline.runner import run_review
from src.pipeline.state import ReviewStatus
from src.retrieval.knowledge import KnowledgeChunk, KnowledgeStore


class FakeLLM:
    def __init__(self, preserve_terms=False):
        self.calls = []
        self.preserve_terms = preserve_terms

    def invoke(self, messages, **kwargs):
        system, user = (message.content for message in messages)
        if "STAGE: EXTRACTION" in system:
            self.calls.append("extraction")
            contract_text = user.split(":\n\n", 1)[1]
            clause_content = contract_text.split("\n", 1)[1]
            payload = {
                "contract_type": "purchase_contract",
                "clauses": [{"title": "1. Payment", "content": clause_content, "category": "payment"}],
                "entities": [],
            }
        elif "STAGE: RISK" in system:
            self.calls.append("risk")
            clause_id = re.search(r"Clause ID: ([^\]]+)", user).group(1)
            payload = {
                "findings": [{"clause_id": clause_id, "risk_level": "medium", "risk_type": "payment_risk", "description": "Payment terms need review", "rationale": "Test candidate"}],
                "overall_risk_level": "medium",
                "risk_summary": "Test candidate",
            }
        elif "STAGE: COMPLIANCE" in system:
            self.calls.append("compliance")
            payload = {"findings": [], "missing_clauses": [], "overall_compliance": "needs_review"}
        elif "STAGE: SUGGESTION" in system:
            self.calls.append("suggestion")
            clause_id = re.search(r"Clause ID=([^\n]+)", user).group(1)
            original = re.search(r"Clause content: .*?: (.*?)\nRisk:", user, re.DOTALL).group(1)
            payload = {"suggestions": [{"clause_id": clause_id, "original_text": original,
                                         "suggested_text": (original + " Payment channel: [proposed channel]." if self.preserve_terms
                                                            else original.replace("30 days", "20 days")),
                                         "reason": "Test candidate", "priority": "medium"}]}
        else:
            raise AssertionError("Unexpected prompt")
        return SimpleNamespace(content=json.dumps(payload, ensure_ascii=False))


def test_four_stage_graph_uses_fake_model_only(monkeypatch):
    fake = FakeLLM(preserve_terms=True)
    chunk = KnowledgeChunk.from_dict({
        "chunk_id": "test-price", "source": "fixture", "title": "Test knowledge", "text": "The price may be agreed by both parties.",
        "url": "https://example.invalid/test", "jurisdiction": "CN-mainland",
        "effective_from": "2021-01-01", "effective_to": None,
        "source_version": "test-v1", "retrieved_at": "2026-10-21",
        "review_status": "reviewed", "keywords": ["price"],
    })
    monkeypatch.setattr(KnowledgeStore, "load", classmethod(lambda cls: KnowledgeStore([chunk])))
    for module in (clause_extraction, risk_identification, compliance_check, suggestion):
        monkeypatch.setattr(module, "get_llm", lambda: fake)

    result = asyncio.run(run_review("1. Payment\nThe price is CNY 1000, payable within 30 days after delivery."))

    assert fake.calls == ["extraction", "risk", "compliance", "suggestion"]
    assert result.status == ReviewStatus.SUCCESS
    assert len(result.clauses) == 1
    assert len(result.risk_findings) == 1
    assert len(result.suggestions) >= 1
    assert result.errors == []
    assert [attempt["stage"] for attempt in result.diagnostics] == ["extraction", "risk", "retrieval", "compliance", "suggestion"]
    assert result.diagnostics[-1]["calls_used"] == 4


def test_two_runs_have_separate_ids_hashes_and_budgets(monkeypatch):
    fake = FakeLLM(preserve_terms=True)
    chunk = KnowledgeChunk.from_dict({
        "chunk_id": "test-price", "source": "fixture", "title": "Test knowledge",
        "text": "The price may be agreed by both parties.", "url": "https://example.invalid/test",
        "jurisdiction": "CN-mainland", "effective_from": "2021-01-01", "effective_to": None,
        "source_version": "test-v1", "retrieved_at": "2026-10-21",
        "review_status": "reviewed", "keywords": ["price"],
    })
    monkeypatch.setattr(KnowledgeStore, "load", classmethod(lambda cls: KnowledgeStore([chunk])))
    for module in (clause_extraction, risk_identification, compliance_check, suggestion):
        monkeypatch.setattr(module, "get_llm", lambda: fake)
    first = asyncio.run(run_review("1. Payment\nThe price is CNY 1000, payable within 30 days after delivery."))
    second = asyncio.run(run_review("1. Payment\nThe price is CNY 2000, payable within 30 days after delivery."))
    assert first.review_id != second.review_id
    assert first.document_hash != second.document_hash
    assert first.status == second.status == ReviewStatus.SUCCESS
    assert first.diagnostics[-1]["calls_used"] == second.diagnostics[-1]["calls_used"] == 4
