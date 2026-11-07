"""Regression checks for sensitive errors and the stateless response contract."""
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from src.api import main
from src.agents import clause_extraction, risk_identification, compliance_check, suggestion
from src.pipeline.state import Clause, ContractReviewState, ReviewStatus, RiskFinding, RiskLevel

MARKER = "SYNTHETIC_PRIVATE_VALUE_DO_NOT_LOG"
TEXT = "The purchase price is CNY 1000."

@pytest.mark.parametrize("module,agent_type", [
    (clause_extraction, clause_extraction.ClauseExtractionAgent),
    (risk_identification, risk_identification.RiskIdentificationAgent),
    (compliance_check, compliance_check.ComplianceCheckAgent),
    (suggestion, suggestion.SuggestionAgent),
])
def test_stage_exception_payloads_are_absent_from_errors_and_logs(monkeypatch, caplog, module, agent_type):
    class BrokenModel:
        def invoke(self, *args, **kwargs):
            raise ValueError(MARKER)
    agent = agent_type()
    agent.llm = BrokenModel()
    clause = Clause(id="c1", title="Payment", content=TEXT, start=0, end=len(TEXT))
    state = ContractReviewState(raw_text=TEXT, contract_type="purchase_contract", clauses=[clause],
        risk_findings=[RiskFinding(clause_id="c1", risk_level=RiskLevel.HIGH, risk_type="payment_risk", description="Candidate concern")])
    result = agent(state)
    assert result["failed_stage"]
    assert MARKER not in json.dumps(result["errors"])
    assert MARKER not in caplog.text
    assert "code=INVALID_MODEL_OUTPUT" in caplog.text


def test_invalid_enum_value_does_not_leak_through_error_or_log(caplog):
    class Model:
        def invoke(self, *args, **kwargs):
            payload = {"contract_type": "purchase_contract", "clauses": [{"title": "Payment", "content": TEXT, "category": MARKER}], "entities": []}
            return SimpleNamespace(content=json.dumps(payload))
    agent = clause_extraction.ClauseExtractionAgent()
    agent.llm = Model()
    result = agent(ContractReviewState(raw_text=TEXT))
    assert result["errors"] == ["INVALID_MODEL_OUTPUT: Model output failed schema or source validation."]
    assert MARKER not in caplog.text


def test_invalid_request_does_not_echo_values(caplog):
    response = TestClient(main.app).post("/api/v1/review", json={"text": {"private": MARKER}})
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_REQUEST"
    assert MARKER not in response.text and MARKER not in caplog.text


def test_unhandled_api_exception_is_not_logged_or_returned(monkeypatch, caplog):
    monkeypatch.setattr(main, "run_review", AsyncMock(side_effect=RuntimeError(MARKER)))
    response = TestClient(main.app).post("/api/v1/review", json={"text": TEXT})
    assert response.status_code == 500
    assert MARKER not in response.text and MARKER not in caplog.text


@pytest.mark.parametrize("status,http_status", [(ReviewStatus.SUCCESS,200), (ReviewStatus.PARTIAL,200), (ReviewStatus.FAILED,502), (ReviewStatus.TIMED_OUT,504)])
@pytest.mark.parametrize("upload", [False,True])
def test_full_result_is_returned_without_retained_history(monkeypatch, status, http_status, upload):
    clause = Clause(id="c1", title="Payment", content=TEXT, start=0, end=len(TEXT))
    state = ContractReviewState(raw_text=TEXT, contract_type="purchase_contract", clauses=[clause], status=status,
        diagnostics=[{"stage":"extraction", "status":"success", "calls_used":1}])
    monkeypatch.setattr(main, "run_review", AsyncMock(return_value=state))
    client = TestClient(main.app)
    response = client.post("/api/v1/review/upload", files={"file":("test.txt",TEXT.encode())}) if upload else client.post("/api/v1/review",json={"text":TEXT})
    assert response.status_code == http_status
    data = response.json()
    assert data["clauses"][0]["content"] == TEXT
    assert data["diagnostics"] == state.diagnostics
    assert data["clauses_count"] == 1
    assert data["status"] == status.value
    assert response.headers["cache-control"] == "no-store"
    assert client.get("/api/v1/review/" + data["review_id"]).status_code == 404
    assert not hasattr(main,"review_store")
