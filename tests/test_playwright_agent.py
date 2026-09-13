"""
test_playwright_agent — Tests for agents/playwright_agent.py (mock + Phase 5 helpers).
Part of: QA Orchestrator
Phase: 5
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


def test_real_mode_calls_run_real_tests(monkeypatch):
    # When USE_MOCK=false, playwright_node delegates to _run_real_tests,
    # not the random simulation path.
    monkeypatch.setenv("USE_MOCK", "false")
    called = {}

    def fake_run_real(state, module_id):
        called["invoked"] = True
        return {"TC-001": {"status": "pass", "duration_ms": 1500}}

    monkeypatch.setattr(playwright_agent, "_run_real_tests", fake_run_real)

    state = _base_state([{"test_case_id": "TC-001", "module": "standard_login", "type": "Smoke"}])
    state = playwright_agent.playwright_node(state)

    assert called.get("invoked") is True
    assert state["ui_results"]["TC-001"]["status"] == "pass"
    assert state["status"] == "ui_complete"


def test_extract_failed_selector_from_locator_call():
    from agents.playwright_agent import _extract_failed_selector
    error = "playwright._impl._errors.TimeoutError: locator('input[name=\"email\"]') exceeded timeout"
    assert _extract_failed_selector(error) == 'input[name="email"]'


def test_extract_failed_selector_from_fill_call():
    from agents.playwright_agent import _extract_failed_selector
    error = "Error in fill('.login-btn', 'value'): element not found"
    assert _extract_failed_selector(error) == ".login-btn"


def test_extract_failed_selector_returns_none_when_no_match():
    from agents.playwright_agent import _extract_failed_selector
    assert _extract_failed_selector("Generic network error, no selector") is None


def test_extract_selector_section_returns_section_8():
    from agents.playwright_agent import _extract_selector_section
    text = "7. API ENDPOINTS\nsome api\n8. UI ELEMENT HINTS\n- Email: input[name='email']\n9. TEST DATA\nsome data"
    result = _extract_selector_section(text)
    assert "input[name='email']" in result
    assert "TEST DATA" not in result


def test_extract_selector_section_falls_back_when_missing():
    from agents.playwright_agent import _extract_selector_section
    text = "x" * 2000
    result = _extract_selector_section(text)
    assert len(result) <= 1500


def test_find_spec_file_returns_none_when_no_match(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "outputs" / "e2e").mkdir(parents=True)
    from agents.playwright_agent import _find_spec_file
    assert _find_spec_file("PROJ-999") is None
