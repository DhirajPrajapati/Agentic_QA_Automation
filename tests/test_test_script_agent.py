"""
test_test_script_agent — Tests for agents/test_script_agent.py.
Part of: QA Orchestrator
Phase: 2
Mock-safe: yes
"""
import json
from pathlib import Path

from agents.analysis_agent import analysis_node
from agents.orchestrator_agent import orchestrator_node
from agents.test_case_agent import test_case_node
from agents.test_script_agent import test_script_node
from graph.state import create_initial_state

# pytest treats any top-level callable named test_* as a test to collect —
# these are fixture-free production functions we call manually below.
test_script_node.__test__ = False
test_case_node.__test__ = False


def _scripted_state(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    state = create_initial_state("PROJ-123")
    state = orchestrator_node(state)
    state = analysis_node(state)
    state = test_case_node(state)
    return test_script_node(state)


def test_ui_scripts_generated_with_test_functions(monkeypatch):
    state = _scripted_state(monkeypatch)
    assert state["ui_scripts"] is not None
    assert "def test_" in state["ui_scripts"]


def test_script_saved_to_outputs_dir(monkeypatch):
    state = _scripted_state(monkeypatch)
    path = Path("outputs/scripts/investor_login_PROJ-123.py")
    assert path.exists()
    assert path.read_text() == state["ui_scripts"]


def test_api_collection_has_negative_cases_added(monkeypatch):
    state = _scripted_state(monkeypatch)
    assert isinstance(state["api_collection"], dict)
    assert "item" in state["api_collection"]
    assert len(state["api_collection"]["item"]) > 2


def test_status_is_scripts_ready(monkeypatch):
    state = _scripted_state(monkeypatch)
    assert state["status"] == "scripts_ready"


def test_recording_content_reaches_llm_unmodified(monkeypatch):
    import agents.test_script_agent as test_script_agent

    captured = {}
    original_recording = Path("recordings/investor/login_happy_path.py").read_text()

    def fake_invoke(messages, agent_type, **kwargs):
        if agent_type == "test_script_ui":
            captured["content"] = messages[0]["content"]
        return "def test_placeholder():\n    pass\n"

    monkeypatch.setattr(test_script_agent, "invoke_with_retry", fake_invoke)
    monkeypatch.setattr(
        test_script_agent, "load_collection", lambda user_type, module: None
    )

    state = create_initial_state("PROJ-123")
    state["jira_data"] = {"fields": {"labels": ["investor", "login"]}}
    state["confluence_context"] = "context"
    state["test_cases"] = [{"id": "TC-001", "flow": "standard_login", "type": "ui"}]

    test_script_agent.test_script_node(state)

    assert original_recording in captured["content"]


def test_no_recording_prepends_warning_comment(monkeypatch, tmp_path):
    import agents.test_script_agent as test_script_agent

    monkeypatch.setattr(
        test_script_agent, "load_recording", lambda user_type, module: None
    )
    monkeypatch.setattr(
        test_script_agent, "load_collection", lambda user_type, module: None
    )
    monkeypatch.setattr(
        test_script_agent,
        "invoke_with_retry",
        lambda messages, agent_type, **kwargs: "def test_generated():\n    pass\n",
    )
    # This test only cares about the warning comment in state["ui_scripts"],
    # not file-saving behavior (covered separately) — avoid writing into the
    # real outputs/scripts/ directory as a side effect.
    monkeypatch.setattr(
        test_script_agent, "_save_script", lambda user_type, module, jira_id, script: tmp_path / "unused.py"
    )

    state = create_initial_state("PROJ-123")
    state["jira_data"] = {"fields": {"labels": ["investor", "dashboard"]}}
    state["confluence_context"] = (
        "8. UI ELEMENT HINTS\nsome hints here\n9. TEST DATA\nirrelevant"
    )
    state["test_cases"] = [{"id": "TC-001", "flow": "dashboard_load", "type": "ui"}]

    state = test_script_agent.test_script_node(state)

    assert state["ui_scripts"].startswith("# WARNING: Generated without recording.")


def test_no_collection_falls_back_to_stub(monkeypatch):
    import agents.test_script_agent as test_script_agent

    monkeypatch.setattr(
        test_script_agent, "load_collection", lambda user_type, module: None
    )
    monkeypatch.setattr(
        test_script_agent,
        "invoke_with_retry",
        lambda messages, agent_type, **kwargs: "def test_x():\n    pass\n",
    )

    state = create_initial_state("PROJ-123")
    state["jira_data"] = {"fields": {"labels": ["investor", "login"]}}
    state["confluence_context"] = "context"
    state["test_cases"] = [{"id": "TC-001", "flow": "standard_login", "type": "ui"}]

    state = test_script_agent.test_script_node(state)

    assert state["api_collection"]["item"] == []


def test_unresolvable_user_type_or_module_does_not_crash(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")

    state = create_initial_state("PROJ-123")
    state["jira_data"] = {"fields": {"labels": ["backend", "urgent"]}}
    state["confluence_context"] = "context"
    state["test_cases"] = []

    from agents.test_script_agent import test_script_node as node

    state = node(state)

    assert state["ui_scripts"] is None
    assert state["status"] == "scripts_ready"
