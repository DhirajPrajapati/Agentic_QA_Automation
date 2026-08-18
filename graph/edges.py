"""
edges — Conditional routing functions for the QA pipeline graph.
Part of: QA Orchestrator
Phase: 2
Mock-safe: yes
"""
from graph.state import QAState


def route_after_scripts(state: QAState) -> str:
    """Route after test_script_agent completes.

    Both branches lead to playwright_agent first — api_agent (Phase 4) runs
    after playwright if skip_api is False, decided by route_after_playwright.
    """
    if state.get("skip_api", False):
        return "ui_only"
    return "both"


def route_after_playwright(state: QAState) -> str:
    """Route after playwright_agent completes: 'run_api' or 'report'."""
    if state.get("skip_api", False):
        return "report"
    return "run_api"
