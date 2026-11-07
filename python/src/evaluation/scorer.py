"""Deterministic risk and missing-clause scorer for reviewed JSONL cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def score_case(case: dict, output: dict) -> dict:
    text = case["input_ref"]["text"]
    expected = case["expected"]
    required = expected["required_findings"]
    scored_risks = set(expected["scored_risk_categories"])
    scored_missing = set(expected["scored_missing_labels"])
    if any(item["category"] not in scored_risks for item in required + expected["forbidden_findings"]):
        raise ValueError("Risk label is outside its scored categories")
    if not set(expected["required_missing_clauses"] + expected["forbidden_missing_clauses"]) <= scored_missing:
        raise ValueError("Missing-clause label is outside its scored labels")
    forbidden_categories = {item["category"] for item in expected["forbidden_findings"]}
    used: set[int] = set()
    tp = fp = fn = 0
    details = []

    for finding in output.get("risk_findings", []):
        category = finding.get("risk_type", "")
        if category not in scored_risks:
            continue
        evidence = finding.get("evidence") or {}
        start, end = evidence.get("start"), evidence.get("end")
        quote = evidence.get("quote")
        valid_span = (
            isinstance(start, int) and not isinstance(start, bool)
            and isinstance(end, int) and not isinstance(end, bool)
            and 0 <= start < end <= len(text) and text[start:end] == quote
        )
        match = next(
            (i for i, item in enumerate(required)
             if i not in used and item["category"] == category and valid_span
             and start <= item["start"] and end >= item["end"]),
            None,
        )
        if match is None:
            fp += 1
            details.append({"kind": "risk", "category": category, "score": "FP",
                            "reason": "forbidden" if category in forbidden_categories else "unmatched_or_invalid_evidence"})
        else:
            tp += 1
            used.add(match)
            details.append({"kind": "risk", "category": category, "score": "TP"})
    for i, item in enumerate(required):
        if i not in used:
            fn += 1
            details.append({"kind": "risk", "category": item["category"], "score": "FN"})

    required_missing = set(expected["required_missing_clauses"])
    forbidden_missing = set(expected["forbidden_missing_clauses"])
    observed_missing = output.get("missing_clauses", [])
    seen_missing = set()
    for label in observed_missing:
        if label not in scored_missing:
            continue
        if label in required_missing and label not in seen_missing:
            tp += 1
            details.append({"kind": "missing", "category": label, "score": "TP"})
        else:
            fp += 1
            details.append({"kind": "missing", "category": label, "score": "FP",
                            "reason": "forbidden" if label in forbidden_missing else "unexpected_or_duplicate"})
        seen_missing.add(label)
    for label in sorted(required_missing - seen_missing):
        fn += 1
        details.append({"kind": "missing", "category": label, "score": "FN"})
    return {"case_id": case["case_id"], "execution_status": output.get("status", "unknown"),
            "tp": tp, "fp": fp, "fn": fn,
            "scored_risk_categories": sorted(scored_risks),
            "scored_missing_labels": sorted(scored_missing), "details": details}


def aggregate(rows: list[dict]) -> dict:
    tp = sum(row["tp"] for row in rows)
    fp = sum(row["fp"] for row in rows)
    fn = sum(row["fn"] for row in rows)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (2 * precision * recall / (precision + recall) if precision + recall else 0.0) if precision is not None and recall is not None else None
    scored_cases = sum(bool(row["scored_risk_categories"] or row["scored_missing_labels"]) for row in rows)
    completed_cases = sum(row["execution_status"] == "success" for row in rows)
    return {"cases": len(rows), "scored_cases": scored_cases,
            "completed_cases": completed_cases, "tp": tp, "fp": fp, "fn": fn,
            "micro_precision": precision, "micro_recall": recall, "micro_f1": f1}


def read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dataset", type=Path)
    parser.add_argument("outputs", type=Path)
    parser.add_argument("--allow-pending", action="store_true", help="Rubric smoke test only; never report as validated model quality")
    args = parser.parse_args()
    cases = read_jsonl(args.dataset)
    if not args.allow_pending and any(case["review_status"] != "reviewed" for case in cases):
        parser.error("Dataset contains unreviewed labels; use --allow-pending only for scorer smoke tests")
    outputs = {row["case_id"]: row for row in read_jsonl(args.outputs)}
    if len(outputs) != len(cases) or {c["case_id"] for c in cases} != set(outputs):
        parser.error("Outputs must have exactly one row for every case_id")
    rows = [score_case(case, outputs[case["case_id"]]) for case in cases]
    print(json.dumps({"summary": aggregate(rows), "rows": rows, "label_status": "unreviewed_smoke" if args.allow_pending else "reviewed"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
