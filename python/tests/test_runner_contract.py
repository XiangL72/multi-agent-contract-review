import asyncio
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from src.api import main
from src.pipeline import runner
from src.pipeline.state import ReviewStatus


def test_text_and_txt_limits_are_shared():
    with pytest.raises(runner.ReviewInputError, match="15000"):
        runner.validate_text("a" * 15_001)
    with pytest.raises(runner.ReviewInputError, match="UTF-8"):
        runner.decode_txt(b"\xff")
    with pytest.raises(runner.ReviewInputError, match="65536"):
        runner.decode_txt(b"a" * 65_537)


def test_runner_rejects_invalid_call_budget_before_start():
    with pytest.raises(ValueError, match="max_calls"):
        asyncio.run(runner.run_review("Synthetic contract", max_calls=9))


def test_api_rejects_unsupported_upload_without_model(monkeypatch):
    async def unexpected(*args, **kwargs):
        raise AssertionError("Runner must not be called")

    monkeypatch.setattr(main, "run_review", unexpected)
    client = TestClient(main.app)
    response = client.post("/api/v1/review/upload", files={"file": ("contract.pdf", b"%PDF")})
    assert response.status_code == 415
    response = client.post("/api/v1/review/upload", files={"file": ("contract.txt", b"\xff")})
    assert response.status_code == 422


def test_extraction_failure_stops_downstream(monkeypatch):
    from src.agents import clause_extraction, risk_identification

    class EmptyExtraction:
        def invoke(self, messages, **kwargs):
            return SimpleNamespace(content=json.dumps({"contract_type": "purchase_contract", "clauses": [], "entities": []}))

    monkeypatch.setattr(clause_extraction, "get_llm", lambda: EmptyExtraction())
    monkeypatch.setattr(risk_identification, "get_llm", lambda: (_ for _ in ()).throw(AssertionError("Risk must not run")))
    result = asyncio.run(runner.run_review("The buyer purchases one unit of equipment."))
    assert result.status == ReviewStatus.FAILED
    assert result.failed_stage == "extraction"
    assert not result.risk_findings


def test_out_of_scope_contract_stops_after_extraction(monkeypatch):
    from src.agents import clause_extraction, risk_identification

    class OtherContract:
        def invoke(self, messages, **kwargs):
            return SimpleNamespace(content=json.dumps({
                "contract_type": "employment_contract",
                "clauses": [{"title": "Term", "content": "The parties agree to an employment term of one year.", "category": "other"}],
                "entities": [],
            }))

    monkeypatch.setattr(clause_extraction, "get_llm", lambda: OtherContract())
    monkeypatch.setattr(risk_identification, "get_llm", lambda: (_ for _ in ()).throw(AssertionError("Risk must not run")))
    result = asyncio.run(runner.run_review("The parties agree to an employment term of one year."))
    assert result.status == ReviewStatus.FAILED
    assert result.failed_stage == "extraction"
    assert "Only purchase/sale contracts are supported" in result.errors[0]


def test_invalid_clause_not_silently_accepted(monkeypatch):
    from src.agents import clause_extraction

    class InventedClause:
        def invoke(self, messages, **kwargs):
            return SimpleNamespace(content=json.dumps({"contract_type": "purchase_contract", "clauses": [{"title": "Invented", "content": "An invented clause absent from the contract", "category": "other"}], "entities": []}))

    monkeypatch.setattr(clause_extraction, "get_llm", lambda: InventedClause())
    result = asyncio.run(runner.run_review("The buyer purchases one unit of equipment."))
    assert result.status == ReviewStatus.FAILED
    assert result.failed_stage == "extraction"
    assert "cannot be located in the source contract" in result.errors[0]


def test_unhandled_graph_exception_becomes_sanitized_failed_result(monkeypatch):
    class BrokenGraph:
        async def ainvoke(self, state, config):
            raise RuntimeError("secret contract content")

    monkeypatch.setattr(runner, "create_review_pipeline", lambda: BrokenGraph())
    result = asyncio.run(runner.run_review("Synthetic contract"))
    assert result.status == ReviewStatus.FAILED
    assert result.failed_stage == "runtime"
    assert result.errors == ["RUNTIME_ERROR"]
