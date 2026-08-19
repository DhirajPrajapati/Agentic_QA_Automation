"""
test_playwright_agent — Tests for agents/playwright_agent.py (mock execution).
Part of: QA Orchestrator
Phase: 2
Mock-safe: yes
"""
import agents.playwright_agent as playwright_agent
from graph.state import create_initial_state

playwright_agent.playwright_node.__test__ = False


def _base_state(test_cases):
    state = create_initial_state("PROJ-123")
    state["jira_data"] = {"fields": {"labels": ["investor", "login"]}}
    state["test_cases"] = test_cases
    return state


def test_all_pass_reports_pass_status_and_duration(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setattr(playwright_agent.random, "choices", lambda *a, **k: ["pass"])

    state = _base_state([{"id": "TC-001", "flow": "standard_login", "type": "ui"}])
    state = playwright_agent.playwright_node(state)

    result = state["ui_results"]["TC-001"]
    assert result["status"] == "pass"
    assert 1200 <= result["duration_ms"] <= 3500


def test_healed_reports_original_and_healed_selectors(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setattr(playwright_agent.random, "choices", lambda *a, **k: ["healed"])

    state = _base_state([{"id": "TC-002", "flow": "otp_trigger", "type": "ui"}])
    state = playwright_agent.playwright_node(state)

    result = state["ui_results"]["TC-002"]
    assert result["status"] == "healed"
    assert 3000 <= result["duration_ms"] <= 5500
    assert result["original_selector"] == ".btn-otp-trigger"
    assert result["healed_selector"] == "button:has-text('Otp Trigger')"
    assert state["errors"] == []


def test_fail_reports_error_and_screenshot_path(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setattr(playwright_agent.random, "choices", lambda *a, **k: ["fail"])

    state = _base_state([{"id": "TC-003", "flow": "otp_verify", "type": "ui"}])
    state = playwright_agent.playwright_node(state)

    result = state["ui_results"]["TC-003"]
    assert result["status"] == "fail"
    assert result["error"] == "Selector not found: .otp_verify-container"
    assert result["screenshot_path"] == "outputs/screenshots/TC-003_fail.png"


def test_runs_every_generated_test_case(monkeypatch):
    # The autonomous test_case schema no longer distinguishes ui/api cases
    # ("type" now means Smoke/Functional/Regression) — every generated case
    # is executed as a UI e2e case.
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setattr(playwright_agent.random, "choices", lambda *a, **k: ["pass"])

    state = _base_state(
        [
            {"test_case_id": "TC-001", "module": "standard_login", "type": "Smoke"},
            {"test_case_id": "TC-004", "module": "otp_verify", "type": "Regression"},
        ]
    )
    state = playwright_agent.playwright_node(state)

    assert set(state["ui_results"].keys()) == {"TC-001", "TC-004"}


def test_sets_status_ui_complete(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setattr(playwright_agent.random, "choices", lambda *a, **k: ["pass"])

    state = _base_state([{"id": "TC-001", "flow": "standard_login", "type": "ui"}])
    state = playwright_agent.playwright_node(state)

    assert state["status"] == "ui_complete"


def test_uses_weighted_random_pass_healed_fail(monkeypatch):
    captured = {}

    def fake_choices(population, weights=None):
        captured["population"] = population
        captured["weights"] = weights
        return ["pass"]

    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setattr(playwright_agent.random, "choices", fake_choices)

    state = _base_state([{"id": "TC-001", "flow": "standard_login", "type": "ui"}])
    playwright_agent.playwright_node(state)

    assert captured["population"] == ["pass", "healed", "fail"]
    assert captured["weights"] == [70, 20, 10]


def test_real_mode_logs_warning_and_still_returns_results(monkeypatch, caplog):
    monkeypatch.setenv("USE_MOCK", "false")
    monkeypatch.setattr(playwright_agent.random, "choices", lambda *a, **k: ["pass"])

    state = _base_state([{"id": "TC-001", "flow": "standard_login", "type": "ui"}])
    with caplog.at_level("WARNING"):
        state = playwright_agent.playwright_node(state)

    assert "TC-001" in state["ui_results"]
    assert any("Phase 5" in record.message for record in caplog.records)
