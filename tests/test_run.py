"""
test_run — Smoke test for run.py CLI entry point.
Part of: QA Orchestrator
Phase: 4
Mock-safe: yes
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_run_cli_prints_test_cases_and_exits_on_result():
    # Mock UI execution is weighted-random (70/20/10 pass/healed/fail), so the
    # exit code legitimately varies run to run — assert it's a valid exit
    # code, not a fixed value.
    env = dict(os.environ, USE_MOCK="true", USE_MOCK_LLM="true")
    result = subprocess.run(
        [sys.executable, "run.py", "--jira", "PROJ-123"],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode in (0, 1), result.stderr
    assert "Generated" in result.stdout
    assert "test cases for PROJ-123" in result.stdout

    json_start = result.stdout.index("[")
    json_end = result.stdout.rindex("]") + 1
    test_cases = json.loads(result.stdout[json_start:json_end])
    assert len(test_cases) >= 4


def test_run_cli_prints_phase_4_output():
    # Log lines go to stderr (logging.basicConfig's default stream) while
    # print() output goes to stdout — merge them, matching what a user
    # actually sees when running this interactively in a terminal.
    env = dict(os.environ, USE_MOCK="true", USE_MOCK_LLM="true")
    result = subprocess.run(
        [sys.executable, "run.py", "--jira", "PROJ-123"],
        cwd=REPO_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=30,
    )

    assert result.returncode in (0, 1), result.stdout
    assert "[test_script] Loaded recording:" in result.stdout
    assert "[playwright] TC-001" in result.stdout
    assert "[api_agent] Mock API results:" in result.stdout
    assert "=== MOCK JIRA COMMENT ===" in result.stdout
    assert "=== MOCK EMAIL ===" in result.stdout
    assert "=== ChromaDB: Learning written ===" in result.stdout
    assert "UI Results: " in result.stdout
    assert "Script saved to: outputs/scripts/investor_login_PROJ-123.py" in result.stdout
