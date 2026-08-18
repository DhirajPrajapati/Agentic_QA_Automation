"""
test_reporter_agent — Tests for agents/reporter_agent.py (Phase 4 full report).
Part of: QA Orchestrator
Phase: 4
Mock-safe: yes
"""
from agents.reporter_agent import reporter_node
from graph.state import create_initial_state

reporter_node.__test__ = False


def _state_with_results():
    state = create_initial_state("PROJ-123")
    state["jira_data"] = {"fields": {"labels": ["investor", "login"]}}
    state["test_cases"] = [
        {"id": "TC-001", "flow": "standard_login", "type": "ui"},
        {"id": "TC-002", "flow": "otp_trigger", "type": "ui"},
        {"id": "TC-003", "flow": "otp_verify", "type": "ui"},
    ]
    state["ui_results"] = {
        "TC-001": {"status": "pass", "duration_ms": 2000},
        "TC-002": {"status": "healed", "duration_ms": 4000, "original_selector": ".btn-a", "healed_selector": "button:has-text('A')"},
        "TC-003": {"status": "fail", "error": "boom", "screenshot_path": "x.png"},
    }
    return state


def test_prints_mock_jira_comment_header(monkeypatch, capsys):
    monkeypatch.setenv("USE_MOCK", "true")
    reporter_node(_state_with_results())
    out = capsys.readouterr().out
    assert "=== MOCK JIRA COMMENT ===" in out
    assert "Agentic QA Report — PROJ-123" in out


def test_prints_each_test_case_with_flow_and_status(monkeypatch, capsys):
    monkeypatch.setenv("USE_MOCK", "true")
    reporter_node(_state_with_results())
    out = capsys.readouterr().out
    assert "TC-001" in out and "standard_login" in out
    assert "TC-002" in out and "otp_trigger" in out and "HEALED" in out
    assert "TC-003" in out and "otp_verify" in out and "boom" in out


def test_prints_ui_summary_line(monkeypatch, capsys):
    monkeypatch.setenv("USE_MOCK", "true")
    reporter_node(_state_with_results())
    out = capsys.readouterr().out
    assert "UI Tests:  1 pass | 1 healed | 1 fail" in out


def test_prints_api_summary_when_present(monkeypatch, capsys):
    monkeypatch.setenv("USE_MOCK", "true")
    state = _state_with_results()
    state["api_results"] = {
        "req-1": {"status": "pass", "name": "req-1", "status_code": 200},
        "req-2": {"status": "pass", "name": "req-2", "status_code": 200},
        "req-3": {"status": "fail", "name": "req-3", "status_code": 500},
    }
    reporter_node(state)
    out = capsys.readouterr().out
    assert "API Tests: 2 pass | 1 fail" in out


def test_omits_api_summary_when_absent(monkeypatch, capsys):
    monkeypatch.setenv("USE_MOCK", "true")
    reporter_node(_state_with_results())
    out = capsys.readouterr().out
    assert "API Tests:" not in out


def test_prints_mock_email_with_subject(monkeypatch, capsys):
    monkeypatch.setenv("USE_MOCK", "true")
    reporter_node(_state_with_results())
    out = capsys.readouterr().out
    assert "=== MOCK EMAIL ===" in out
    assert "Subject: QA Report: PROJ-123" in out


def test_prints_chromadb_learning_written(monkeypatch, capsys):
    monkeypatch.setenv("USE_MOCK", "true")
    reporter_node(_state_with_results())
    out = capsys.readouterr().out
    assert "=== ChromaDB: Learning written ===" in out


def test_sets_status_complete(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    state = reporter_node(_state_with_results())
    assert state["status"] == "complete"


def test_logs_run_complete(monkeypatch, caplog):
    monkeypatch.setenv("USE_MOCK", "true")
    with caplog.at_level("INFO"):
        reporter_node(_state_with_results())
    assert "Run complete for PROJ-123" in caplog.text
