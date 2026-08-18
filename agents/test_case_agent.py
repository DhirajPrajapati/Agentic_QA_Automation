"""
test_case_agent — Generates structured test cases per flow via the LLM.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import json
import logging

from graph.state import QAState
from tools.llm_client import invoke_with_retry

logger = logging.getLogger(__name__)


def _build_prompt(state: QAState, flow: str) -> list[dict[str, str]]:
    """Build the per-flow test case prompt from Confluence, AC, and risk areas."""
    fields = state["jira_data"].get("fields", {})
    acceptance_criteria = fields.get("acceptance_criteria", [])
    content = (
        f"Flow: {flow}\n"
        f"Acceptance criteria: {acceptance_criteria}\n"
        f"Risk areas: {state['risk_areas']}\n"
        f"Confluence edge cases (Section 6):\n{state['confluence_context']}\n\n"
        "Output ONLY a valid JSON array of test case objects. No markdown.\n"
        "Each object: id, flow, priority, given, when, then, type. "
        "Minimum 1 P1 happy path + 1 P2 negative case."
    )
    return [{"role": "user", "content": content}]


def test_case_node(state: QAState) -> QAState:
    """Generate test cases for every flow in state['flows_to_test']."""
    all_cases: list[dict] = []
    try:
        for flow in state["flows_to_test"]:
            raw = invoke_with_retry(messages=_build_prompt(state, flow), agent_type="test_case")
            try:
                cases = json.loads(raw)
            except json.JSONDecodeError as e:
                logger.error("[test_case] Failed to parse LLM JSON for flow=%s: %s", flow, str(e))
                cases = []

            for case in cases:
                case["flow"] = flow
                all_cases.append(case)

        for index, case in enumerate(all_cases, start=1):
            case["id"] = f"TC-{index:03d}"

        state["test_cases"] = all_cases
        state["status"] = "test_cases_complete"
        state["current_phase"] = "test_case"

        priorities = [c.get("priority") for c in all_cases]
        breakdown = {p: priorities.count(p) for p in sorted(set(priorities))}
        logger.info(
            "[test_case] Generated %d test cases — breakdown: %s", len(all_cases), breakdown
        )
    except Exception as e:
        logger.error("[test_case] Call failed: %s", str(e))
        state["errors"].append({"agent": "test_case", "error": str(e)})
        state["test_cases"] = all_cases

    return state
