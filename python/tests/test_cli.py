import json
import subprocess
import sys


def test_mock_cli_runs_in_fresh_process_without_provider(tmp_path):
    output = tmp_path / "review.json"
    run = subprocess.run(
        [sys.executable, "-m", "src.cli", "--mock", "--text", "The seller assumes unlimited liability. The price is CNY 1000.",
         "--output", str(output)],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert run.returncode == 0, run.stderr
    data = json.loads(output.read_text())
    assert data["mock"] is True
    assert data["result"]["status"] == "success"
    assert data["result"]["knowledge_status"] == "grounded"
    assert len(data["result"]["risk_findings"]) >= 1
    assert data["result"]["diagnostics"][-1]["calls_used"] <= 8


def test_cli_requires_explicit_model_mode():
    run = subprocess.run([sys.executable, "-m", "src.cli", "--text", "Synthetic contract"],
                         capture_output=True, text=True, timeout=20, check=False)
    assert run.returncode != 0
    assert "--mock" in run.stderr and "--real" in run.stderr


def test_mock_cli_marks_unmatched_knowledge_partial():
    run = subprocess.run(
        [sys.executable, "-m", "src.cli", "--mock", "--text", "The seller assumes unlimited liability."],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert run.returncode == 2, run.stderr
    data = json.loads(run.stdout)
    assert data["result"]["knowledge_status"] == "evidence_insufficient"
    assert not any(row["stage"] == "compliance" for row in data["result"]["diagnostics"])
