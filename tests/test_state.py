"""
test_state — Tests for graph/state.py QAState factory.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
from graph.state import create_initial_state


def test_create_initial_state_sets_jira_id():
    state = create_initial_state("PROJ-123")
    assert state["jira_id"] == "PROJ-123"


def test_create_initial_state_sets_initial_status():
    state = create_initial_state("PROJ-123")
    assert state["status"] == "initialising"


def test_create_initial_state_defaults_collections_to_empty():
    state = create_initial_state("PROJ-123")
    assert state["jira_data"] == {}
    assert state["confluence_context"] == ""
    assert state["past_failures"] == []
    assert state["flows_to_test"] == []
    assert state["risk_areas"] == []
    assert state["user_types_in_scope"] == []
    assert state["test_cases"] == []
    assert state["errors"] == []
    assert state["retry_count"] == 0
    assert state["skip_api"] is False
    assert state["ui_scripts"] is None
    assert state["api_collection"] is None
    assert state["ui_results"] is None
    assert state["api_results"] is None
