from src.agents.risk_identification import RiskIdentificationAgent
from src.pipeline.state import Clause


def test_negated_unlimited_liability_does_not_trigger_rule():
    clause = Clause(id="c1", title="Liability", content="The seller does not assume unlimited liability; damages are capped at the price received.", start=0, end=23)
    assert not any(f.risk_type == "unlimited_liability" for f in RiskIdentificationAgent()._rule_based_scan([clause]))


def test_later_positive_occurrence_is_not_hidden_by_negation():
    clause = Clause(id="c1", title="Liability", content="The seller does not assume unlimited liability; the buyer assumes unlimited liability.")
    assert any(f.risk_type == "unlimited_liability" for f in RiskIdentificationAgent()._rule_based_scan([clause]))
