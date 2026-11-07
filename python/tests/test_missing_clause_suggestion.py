from src.agents import suggestion
from src.pipeline.state import ContractReviewState


def test_missing_clause_alone_produces_addition_without_model(monkeypatch):
    def unexpected_model():
        raise AssertionError("Missing-only suggestions must not call a model")

    monkeypatch.setattr(suggestion, "get_llm", unexpected_model)
    state = ContractReviewState(missing_clauses=["Price"])

    result = suggestion.SuggestionAgent()(state)

    assert len(result["suggestions"]) == 1
    assert result["suggestions"][0].clause_id == "new"
    assert "Price" in result["suggestions"][0].reason
    assert "Addition" in result["version_diff"]
