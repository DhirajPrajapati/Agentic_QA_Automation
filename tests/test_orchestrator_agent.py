"""
test_orchestrator_agent — Tests for agents/orchestrator_agent.py.
Part of: QA Orchestrator
Phase: 3
Mock-safe: yes
"""
from agents.orchestrator_agent import orchestrator_node
from graph.state import create_initial_state


def test_orchestrator_fetches_jira_and_confluence(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    state = orchestrator_node(create_initial_state("PROJ-123"))
    assert state["jira_data"]["id"] == "PROJ-123"
    assert len(state["confluence_context"]) > 100
    assert state["status"] == "orchestrator_complete"
    # ChromaDB is always real (never mocked), so past_failures reflects
    # whatever learnings already exist locally — just assert the shape.
    assert isinstance(state["past_failures"], list)
    assert state["errors"] == []


def test_orchestrator_records_error_on_missing_ticket(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    state = orchestrator_node(create_initial_state("NO-SUCH-TICKET"))
    assert len(state["errors"]) == 1
    assert state["errors"][0]["agent"] == "orchestrator"
