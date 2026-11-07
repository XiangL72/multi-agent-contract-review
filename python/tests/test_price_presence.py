"""English presence heuristics: explicit price, quantity, and long-text boundaries."""
import json
from pathlib import Path
import pytest
from src.agents.compliance_check import ComplianceCheckAgent
from src.pipeline.state import Clause

CASES = json.loads((Path(__file__).resolve().parents[2] / "evals/price-presence/cases.json").read_text())["cases"]

@pytest.mark.parametrize("case", CASES, ids=lambda case: case["case_id"])
def test_price_presence(case):
    clause = Clause(**{key: case["input_ref"][key] for key in ("title", "content", "category")})
    missing = ComplianceCheckAgent()._check_missing_clauses([clause], "purchase_contract")
    assert ("Price" not in missing) == case["expected"]["price_present"]

def test_separate_penalty_does_not_erase_price():
    clauses = [Clause(title="Payment", content="The price is CNY 1000."), Clause(title="Penalty", content="The penalty is CNY 100.")]
    assert "Price" not in ComplianceCheckAgent()._check_missing_clauses(clauses, "purchase_contract")

def test_missing_price_is_explicit():
    assert "Price" in ComplianceCheckAgent()._check_missing_clauses([], "purchase_contract")

def test_quantity_requires_an_explicit_count():
    agent = ComplianceCheckAgent()
    assert "Quantity" in agent._check_missing_clauses([Clause(title="Goods", content="Equipment quantity remains to be determined.")], "purchase_contract")
    assert "Quantity" not in agent._check_missing_clauses([Clause(title="Goods", content="The buyer purchases one unit of equipment.")], "purchase_contract")

def test_late_terms_are_not_truncated():
    clause = Clause(title="Purchase", content="The buyer purchases one unit of equipment. " + "Other terms apply. " * 12 + "Breach liability rests with the party in breach. Disputes go to arbitration.")
    missing = ComplianceCheckAgent()._check_missing_clauses([clause], "purchase_contract")
    assert "Breach liability" not in missing and "Dispute resolution" not in missing
