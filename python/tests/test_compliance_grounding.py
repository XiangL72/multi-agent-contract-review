import json
from types import SimpleNamespace

from src.agents.compliance_check import ComplianceCheckAgent
from src.pipeline.state import Clause, ContractReviewState
from src.retrieval.knowledge import KnowledgeChunk, KnowledgeStore


class FakeLLM:
    def __init__(self, payload):
        self.payload = payload
        self.calls = 0

    def invoke(self, messages, **kwargs):
        self.calls += 1
        assert "civil-code-510" in messages[-1].content
        return SimpleNamespace(content=json.dumps(self.payload, ensure_ascii=False))


def _state():
    text = "The price is not agreed; negotiate after delivery."
    return ContractReviewState(raw_text=text, contract_type="purchase_contract",
                               clauses=[Clause(id="c1", title="Price", content=text,
                                               start=0, end=len(text))])


def _reviewed_store():
    return KnowledgeStore([KnowledgeChunk.from_dict({
        "chunk_id": "civil-code-510", "source": "fixture", "title": "PRC Civil Code Article 510",
        "text": "An unspecified price may be supplemented by agreement.", "url": "https://example.invalid/510",
        "jurisdiction": "CN-mainland", "effective_from": "2021-01-01",
        "effective_to": None, "source_version": "test-v1", "retrieved_at": "2026-10-21",
        "review_status": "reviewed", "keywords": ["Price"],
    })])


def test_valid_citation_is_attached_to_contract_evidence(monkeypatch):
    monkeypatch.setattr(KnowledgeStore, "load", classmethod(lambda cls: _reviewed_store()))
    state = _state()
    llm = FakeLLM({"findings": [{"clause_id": "c1", "status": "needs_review",
                                "regulation": "PRC Civil Code Article 510", "issue": "Price needs clarification",
                                "recommendation": "Agree on the price",
                                "citations": [{"chunk_id": "civil-code-510",
                                               "source_version": "test-v1", "quote": "may be supplemented by agreement"}]}]})
    agent = ComplianceCheckAgent()
    agent.llm = llm
    result = agent(state)
    assert llm.calls == 1
    assert result["knowledge_status"] == "grounded"
    assert result["compliance_findings"][0].evidence.quote == state.raw_text
    assert result["compliance_findings"][0].knowledge_citations[0]["url"] == "https://example.invalid/510"


def test_invented_citation_is_isolated(monkeypatch):
    monkeypatch.setattr(KnowledgeStore, "load", classmethod(lambda cls: _reviewed_store()))
    llm = FakeLLM({"findings": [{"clause_id": "c1", "status": "non_compliant",
                                "issue": "Candidate issue", "citations": [{"chunk_id": "invented",
                                "source_version": "test-v1", "quote": "may be supplemented by agreement"}]}]})
    agent = ComplianceCheckAgent()
    agent.llm = llm
    result = agent(_state())
    assert result["compliance_findings"] == []
    assert result["knowledge_status"] == "invalid_citations"


def test_no_eligible_knowledge_skips_model(monkeypatch):
    pending = KnowledgeChunk.from_dict({
        "chunk_id": "pending", "source": "fixture", "title": "Pending review", "text": "Price", "url": "https://example.invalid",
        "jurisdiction": "CN-mainland", "effective_from": "2021-01-01",
        "effective_to": None, "source_version": "test-v1", "retrieved_at": "2026-10-21", "review_status": "pending",
        "keywords": ["Price"],
    })
    monkeypatch.setattr(KnowledgeStore, "load", classmethod(lambda cls: KnowledgeStore([pending])))
    agent = ComplianceCheckAgent()
    agent.llm = FakeLLM({"findings": []})
    result = agent(_state())
    assert agent.llm.calls == 0
    assert result["knowledge_status"] == "evidence_insufficient"
