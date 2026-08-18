"""
test_test_case_agent — Tests for agents/test_case_agent.py.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
from agents.analysis_agent import analysis_node
from agents.orchestrator_agent import orchestrator_node
from agents.test_case_agent import test_case_node
from graph.state import create_initial_state

# pytest treats any top-level callable named test_* as a test to collect —
# this one is a fixture-free production function we call manually below.
test_case_node.__test__ = False


def _full_chain_state(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    state = create_initial_state("PROJ-123")
    state = orchestrator_node(state)
    state = analysis_node(state)
    return test_case_node(state)


def test_test_case_generates_at_least_four_cases(monkeypatch):
    state = _full_chain_state(monkeypatch)
    assert len(state["test_cases"]) >= 4


def test_test_case_includes_p1_and_p2(monkeypatch):
    state = _full_chain_state(monkeypatch)
    priorities = {tc["priority"] for tc in state["test_cases"]}
    assert "P1" in priorities
    assert "P2" in priorities


def test_test_case_ids_are_unique_and_sequential(monkeypatch):
    state = _full_chain_state(monkeypatch)
    ids = [tc["id"] for tc in state["test_cases"]]
    assert ids == [f"TC-{i:03d}" for i in range(1, len(ids) + 1)]


def test_test_case_flow_matches_requested_flow(monkeypatch):
    state = _full_chain_state(monkeypatch)
    requested_flows = set(state["flows_to_test"])
    for tc in state["test_cases"]:
        assert tc["flow"] in requested_flows


def test_test_case_sets_status_complete(monkeypatch):
    state = _full_chain_state(monkeypatch)
    assert state["status"] == "test_cases_complete"


def test_test_case_handles_malformed_llm_json(monkeypatch):
    import agents.test_case_agent as test_case_agent

    monkeypatch.setattr(test_case_agent, "invoke_with_retry", lambda **kwargs: "not valid json")
    state = create_initial_state("PROJ-123")
    state["flows_to_test"] = ["standard_login"]
    state["jira_data"] = {"fields": {"acceptance_criteria": []}}
    state["confluence_context"] = ""
    state["risk_areas"] = []

    state = test_case_agent.test_case_node(state)

    assert state["test_cases"] == []
    assert state["status"] == "test_cases_complete"
