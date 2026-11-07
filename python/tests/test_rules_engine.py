# Modified for the English text/TXT demo; scope and behavior are documented in README.md.
"""Contract review workflow support."""

import pytest

from src.rules.engine import RuleEngine, RuleSeverity


@pytest.fixture
def engine():
    return RuleEngine()


class TestRuleEngine:
    def test_unlimited_liability_detected(self, engine):
        results = engine.evaluate_clause("The seller bears all losses with no liability cap.")
        assert any(r.severity == RuleSeverity.CRITICAL for r in results)

    def test_unilateral_termination_detected(self, engine):
        results = engine.evaluate_clause("The buyer may unilaterally terminate the contract.")
        assert any("unilaterally terminate" in r.message or r.rule_id == "R002" for r in results)

    def test_no_risk_in_normal_clause(self, engine):
        results = engine.evaluate_clause("Both parties shall perform their agreed obligations.")
        assert len(results) == 0

    def test_vague_terms_detected(self, engine):
        results = engine.evaluate_clause("The amount remains subject to further agreement.")
        assert any(r.severity == RuleSeverity.INFO for r in results)

    def test_format_clause_invalid(self, engine):
        results = engine.evaluate_clause("This clause excludes own liability.")
        critical = [r for r in results if r.severity == RuleSeverity.CRITICAL]
        assert len(critical) > 0

    def test_auto_renewal_detected(self, engine):
        results = engine.evaluate_clause("The contract renews automatically for one year.")
        assert len(results) > 0

    def test_statistics(self, engine):
        stats = engine.get_statistics()
        assert stats["total_rules"] > 0
        assert "by_severity" in stats
        assert "by_category" in stats
