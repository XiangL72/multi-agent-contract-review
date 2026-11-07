from src.evaluation.scorer import aggregate, score_case


def test_scoring_requires_evidence_and_counts_duplicate_once():
    text = "The seller assumes unlimited liability."
    case = {
        "case_id": "x",
        "input_ref": {"text": text},
        "expected": {
            "required_findings": [{"category": "unlimited_liability", "start": 0, "end": len(text) - 1}],
            "forbidden_findings": [],
            "required_missing_clauses": ["Price"],
            "forbidden_missing_clauses": [],
            "scored_risk_categories": ["unlimited_liability"],
            "scored_missing_labels": ["Price"],
        },
    }
    finding = {"risk_type": "unlimited_liability", "evidence": {"start": 0, "end": len(text), "quote": text}}
    row = score_case(case, {"risk_findings": [finding, finding], "missing_clauses": ["Price", "Price"]})
    assert (row["tp"], row["fp"], row["fn"]) == (2, 2, 0)
    assert aggregate([row])["micro_f1"] == 2 / 3


def test_empty_case_has_no_invented_perfect_score():
    row = score_case({"case_id": "empty", "input_ref": {"text": "No obvious concerns."}, "expected": {"required_findings": [], "forbidden_findings": [], "required_missing_clauses": [], "forbidden_missing_clauses": [], "scored_risk_categories": [], "scored_missing_labels": []}}, {})
    assert aggregate([row])["micro_f1"] is None


def test_unreviewed_categories_are_outside_score_scope():
    case = {"case_id": "limited", "input_ref": {"text": "The price is CNY 1000"},
            "expected": {"required_findings": [], "forbidden_findings": [],
                         "required_missing_clauses": [], "forbidden_missing_clauses": ["Price"],
                         "scored_risk_categories": [], "scored_missing_labels": ["Price"]}}
    output = {"risk_findings": [{"risk_type": "payment_risk"}],
              "missing_clauses": ["Dispute resolution"]}
    row = score_case(case, output)
    assert (row["tp"], row["fp"], row["fn"]) == (0, 0, 0)


def test_partial_execution_is_reported_even_when_one_label_matches():
    case = {"case_id": "partial", "input_ref": {"text": "The price is not agreed"},
            "expected": {"required_findings": [], "forbidden_findings": [],
                         "required_missing_clauses": ["Price"], "forbidden_missing_clauses": [],
                         "scored_risk_categories": [], "scored_missing_labels": ["Price"]}}
    row = score_case(case, {"status": "partial", "missing_clauses": ["Price"]})
    assert row["tp"] == 1
    assert aggregate([row])["completed_cases"] == 0
