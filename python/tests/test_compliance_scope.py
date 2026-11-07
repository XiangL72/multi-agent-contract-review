"""Narrow review policy: matching a quote cannot license legal-validity assertions."""
import asyncio
import json
from types import SimpleNamespace

import pytest

from src.agents import clause_extraction, compliance_check, risk_identification, suggestion
from src.agents.compliance_check import ComplianceCheckAgent
from src.demo.fake_llm import DemoLLM
from src.harness.execution import ExecutionContext, reset_execution, set_execution
from src.pipeline.graph import complete_node
from src.pipeline.runner import run_review
from src.pipeline.state import Clause, ContractReviewState, ReviewStatus
from src.retrieval.knowledge import KnowledgeChunk, KnowledgeStore


TEXT = "The price is not agreed."


def source_store():
    return KnowledgeStore([KnowledgeChunk.from_dict({
        "chunk_id": "civil-code-510", "source": "fixture", "title": "Source summary 510",
        "text": "An unspecified price may be supplemented by agreement.",
        "url": "https://example.invalid/510", "jurisdiction": "CN-mainland",
        "effective_from": "2021-01-01", "effective_to": None,
        "source_version": "fixture-v1", "retrieved_at": "2026-10-21",
        "review_status": "reviewed", "keywords": ["price"],
    })])


def finding(**overrides):
    return {"clause_id": "c1", "status": "needs_review",
            "regulation": "Model-supplied authority label",
            "issue": "The price needs clarification.",
            "recommendation": "Consider agreeing the price in supplementary terms.",
            "citations": [{"chunk_id": "civil-code-510", "source_version": "fixture-v1",
                           "quote": "may be supplemented by agreement"}], **overrides}


def check(monkeypatch, findings):
    monkeypatch.setattr(KnowledgeStore, "load", classmethod(lambda cls: source_store()))
    class Fake:
        def invoke(self, *args, **kwargs):
            # Deliberately challenge the requested overall status.
            return SimpleNamespace(content=json.dumps({"findings": findings, "overall_compliance": "compliant"}))
    agent = ComplianceCheckAgent()
    agent.llm = Fake()
    clause = Clause(id="c1", title="Price", content=TEXT, start=0, end=len(TEXT))
    state = ContractReviewState(raw_text=TEXT, contract_type="purchase_contract", clauses=[clause])
    return agent(state)


@pytest.mark.parametrize("issue", [
    "The arbitration agreement may be invalid without a named commission.",
    "The contract is unenforceable.",
    "This is a mandatory contract term.",
    "The buyer must add a deposit.",
    "A late fee is required by law.",
    "This is in violation of arbitration rules.",
])
def test_matching_quote_does_not_admit_obvious_legal_assertions(monkeypatch, issue):
    result = check(monkeypatch, [finding(issue=issue)])
    assert result["compliance_findings"] == []
    assert result["knowledge_status"] == "out_of_scope_findings"
    assert result["overall_compliance"].value == "needs_review"
    assert complete_node(ContractReviewState(**result))["status"] == ReviewStatus.PARTIAL


@pytest.mark.parametrize("status", ["compliant", "non_compliant"])
def test_legal_verdict_is_rejected_not_relabelled(monkeypatch, status):
    result = check(monkeypatch, [finding(status=status)])
    assert not result["compliance_findings"]
    assert result["knowledge_status"] == "out_of_scope_findings"


def test_supported_candidate_keeps_evidence_and_trusted_source_label(monkeypatch):
    result = check(monkeypatch, [finding()])
    kept = result["compliance_findings"][0]
    assert kept.status.value == "needs_review"
    assert kept.regulation == "Source summary 510"
    assert kept.evidence.quote == TEXT
    assert kept.knowledge_citations[0]["quote"] == "may be supplemented by agreement"
    assert result["overall_compliance"].value == "needs_review"


def test_rejected_claim_does_not_remove_valid_candidate_or_hide_partial(monkeypatch):
    context = ExecutionContext()
    token = set_execution(context)
    try:
        result = check(monkeypatch, [finding(issue="The agreement is invalid."), finding()])
    finally:
        reset_execution(token)
    assert len(result["compliance_findings"]) == 1
    assert result["knowledge_status"] == "out_of_scope_findings"
    assert any(d.get("error_code") == "COMPLIANCE_SCOPE_REJECTED" and d["invalid_findings"] == 1 for d in context.attempts)


def test_bad_citation_still_fails_before_scope_screening(monkeypatch):
    result = check(monkeypatch, [finding(citations=[{"chunk_id": "invented", "source_version": "fixture-v1", "quote": "may be supplemented by agreement"}])])
    assert not result["compliance_findings"]
    assert result["knowledge_status"] == "invalid_citations"


def test_no_findings_is_not_an_affirmative_compliance_verdict(monkeypatch):
    result = check(monkeypatch, [])
    assert result["compliance_findings"] == []
    assert result["overall_compliance"].value == "needs_review"


def test_recommendation_and_authority_are_also_screened(monkeypatch):
    result = check(monkeypatch, [finding(recommendation="You must add a deposit.")])
    assert not result["compliance_findings"]
    result = check(monkeypatch, [finding(regulation="Mandatory arbitration requirements")])
    assert not result["compliance_findings"]


def test_graph_retains_partial_and_does_not_send_rejected_claim_to_suggestions(monkeypatch):
    class Fake(DemoLLM):
        def invoke(self, messages, **kwargs):
            if "STAGE: COMPLIANCE" in messages[0].content:
                import re
                clause_id = re.search(r"\[Clause ID: ([^\]]+)\]", messages[-1].content).group(1)
                return SimpleNamespace(content=json.dumps({"findings": [finding(clause_id=clause_id, issue="The contract is invalid.")]}))
            if "STAGE: SUGGESTION" in messages[0].content:
                raise AssertionError("Rejected compliance claim must not trigger a revision call")
            return super().invoke(messages, **kwargs)
    monkeypatch.setattr(KnowledgeStore, "load", classmethod(lambda cls: source_store()))
    fake = Fake()
    for module in (clause_extraction, risk_identification, compliance_check, suggestion):
        monkeypatch.setattr(module, "get_llm", lambda: fake)
    result = asyncio.run(run_review(TEXT))
    assert result.status == ReviewStatus.PARTIAL
    assert result.knowledge_status == "out_of_scope_findings"
    assert result.compliance_findings == []
    assert all(item.kind == "addition" for item in result.suggestions)
    assert max(d.get("calls_used", 0) for d in result.diagnostics) == 3
