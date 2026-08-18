"""
test_graph_builder — Tests for graph/graph_builder.py (Phase 4 full graph).
Part of: QA Orchestrator
Phase: 4
Mock-safe: yes
"""
from graph.graph_builder import build_graph
from graph.state import create_initial_state


def test_graph_runs_end_to_end_through_reporter(monkeypatch, capsys):
    monkeypatch.setenv("USE_MOCK", "true")
    monkeypatch.setenv("USE_MOCK_LLM", "true")

    graph = build_graph()
    final_state = graph.invoke(create_initial_state("PROJ-123"))

    assert final_state["status"] == "complete"
    assert len(final_state["test_cases"]) >= 4
    assert final_state["ui_scripts"] is not None
    assert final_state["ui_results"] is not None
    assert len(final_state["ui_results"]) > 0
    assert final_state["api_collection"] is not None
    assert final_state["api_results"] is not None
    assert final_state["errors"] == []

    out = capsys.readouterr().out
    assert "=== MOCK JIRA COMMENT ===" in out
    assert "=== MOCK EMAIL ===" in out
    assert "=== ChromaDB: Learning written ===" in out
