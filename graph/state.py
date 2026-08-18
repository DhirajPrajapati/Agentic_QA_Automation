"""
state — QAState TypedDict and initial-state factory.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
from typing import Optional, TypedDict


class QAState(TypedDict):
    """Single shared state object threaded through every node in the graph."""

    # Inputs — written by orchestrator_agent
    jira_id: str
    jira_data: dict
    confluence_context: str
    past_failures: list

    # Analysis — written by analysis_agent
    flows_to_test: list
    skip_api: bool
    risk_areas: list
    user_types_in_scope: list

    # Generation — written by test_case_agent + test_script_agent
    test_cases: list
    ui_scripts: Optional[str]
    api_collection: Optional[dict]

    # Execution — written by playwright_agent + api_agent
    ui_results: Optional[dict]
    api_results: Optional[dict]

    # Control — managed by orchestrator + each agent
    status: str
    retry_count: int
    errors: list
    current_phase: str


def create_initial_state(jira_id: str) -> QAState:
    """Build a fresh QAState for a new pipeline run, keyed by jira_id."""
    return QAState(
        jira_id=jira_id,
        jira_data={},
        confluence_context="",
        past_failures=[],
        flows_to_test=[],
        skip_api=False,
        risk_areas=[],
        user_types_in_scope=[],
        test_cases=[],
        ui_scripts=None,
        api_collection=None,
        ui_results=None,
        api_results=None,
        status="initialising",
        retry_count=0,
        errors=[],
        current_phase="init",
    )
