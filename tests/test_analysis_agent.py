"""
test_analysis_agent — Tests for agents/analysis_agent.py.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
from agents.analysis_agent import analysis_node
from agents.orchestrator_agent import orchestrator_node
from graph.state import create_initial_state


def _analyzed_state(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    state = orchestrator_node(create_initial_state("PROJ-123"))
    return analysis_node(state)


def test_analysis_writes_flows_and_scope(monkeypatch):
    state = _analyzed_state(monkeypatch)
    assert len(state["flows_to_test"]) > 0
    assert isinstance(state["skip_api"], bool)
    assert isinstance(state["risk_areas"], list)
    assert isinstance(state["user_types_in_scope"], list)
    assert state["status"] == "analysis_complete"


def test_analysis_skip_api_false_when_labels_include_backend_terms(monkeypatch):
    # PROJ-123 labels: investor, login, otp, frontend — not purely frontend.
    state = _analyzed_state(monkeypatch)
    assert state["skip_api"] is False


def test_analysis_skip_api_true_when_labels_are_frontend_only(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    state = create_initial_state("PROJ-123")
    state["jira_data"] = {"fields": {"labels": ["frontend", "ui"]}}
    state["confluence_context"] = "some context"
    state["past_failures"] = []
    state = analysis_node(state)
    assert state["skip_api"] is True


def test_analysis_handles_malformed_llm_json(monkeypatch):
    import agents.analysis_agent as analysis_agent

    monkeypatch.setattr(analysis_agent, "invoke_with_retry", lambda **kwargs: "not valid json")
    state = create_initial_state("PROJ-123")
    state["jira_data"] = {"fields": {"labels": ["investor", "login"]}}
    state["confluence_context"] = "some context"
    state["past_failures"] = []

    state = analysis_node(state)

    assert state["flows_to_test"] == []
    assert state["risk_areas"] == []
    assert state["user_types_in_scope"] == []
    assert state["status"] == "analysis_complete"
