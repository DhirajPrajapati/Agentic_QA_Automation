"""
test_edges — Tests for graph/edges.py conditional routing (Phase 2).
Part of: QA Orchestrator
Phase: 2
Mock-safe: yes
"""
from graph.edges import route_after_playwright, route_after_scripts
from graph.state import create_initial_state


def test_route_after_scripts_ui_only_when_skip_api():
    state = create_initial_state("PROJ-123")
    state["skip_api"] = True
    assert route_after_scripts(state) == "ui_only"


def test_route_after_scripts_both_when_not_skip_api():
    state = create_initial_state("PROJ-123")
    state["skip_api"] = False
    assert route_after_scripts(state) == "both"


def test_route_after_playwright_report_when_skip_api():
    state = create_initial_state("PROJ-123")
    state["skip_api"] = True
    assert route_after_playwright(state) == "report"


def test_route_after_playwright_run_api_when_not_skip_api():
    state = create_initial_state("PROJ-123")
    state["skip_api"] = False
    assert route_after_playwright(state) == "run_api"
