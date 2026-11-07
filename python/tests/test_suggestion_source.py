import json
from types import SimpleNamespace

from src.agents.suggestion import SuggestionAgent
from src.pipeline.state import Clause, RiskFinding, RiskLevel


class FakeLLM:
    def invoke(self, messages):
        return SimpleNamespace(content=json.dumps({"suggestions": [{
            "clause_id": "c1", "original_text": "Source text invented by the model",
            "suggested_text": "The price is payable 30 days after delivery.",
            "reason": "Specify payment terms", "priority": "medium"}]}))


def test_original_text_is_taken_from_verified_clause_not_model_echo():
    agent = SuggestionAgent()
    agent.llm = FakeLLM()
    clause = Clause(id="c1", title="Payment", content="The price is payable after delivery.")
    finding = RiskFinding(clause_id="c1", risk_level=RiskLevel.MEDIUM,
                          risk_type="payment_risk", description="Payment date is unclear")
    result = agent._generate_suggestions([clause], [finding], [])
    assert result[0].original_text == clause.content
    assert result[0].suggested_text == "The price is payable 30 days after delivery."
