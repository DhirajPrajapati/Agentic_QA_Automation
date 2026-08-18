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

    # === Attach test cases to Jira ticket immediately ===
    # QA team can review cases while pipeline continues running
    try:
        from pathlib import Path
        from tools.jira_client import (
            attach_file_to_ticket,
            format_test_cases_as_text,
        )

        summary = state["jira_data"].get("fields", {}).get("summary", "")
        tc_text = format_test_cases_as_text(
            test_cases=state["test_cases"],
            jira_id=state["jira_id"],
            jira_summary=summary,
        )

        # Save formatted file locally
        tc_file_name = f"{state['jira_id']}_test_cases.txt"
        tc_file_path = Path(f"outputs/reports/{tc_file_name}")
        tc_file_path.parent.mkdir(parents=True, exist_ok=True)
        tc_file_path.write_text(tc_text)
        logger.info("[test_case] Test cases saved: %s", tc_file_path)

        # Attach to Jira immediately
        attached = attach_file_to_ticket(
            jira_id=state["jira_id"],
            file_path=str(tc_file_path),
            file_name=tc_file_name,
        )

        if attached:
            state["tc_attachment_name"] = tc_file_name
            logger.info(
                "[test_case] Test cases attached to Jira: %s — "
                "QA team can review while pipeline runs",
                tc_file_name,
            )
        else:
            state["tc_attachment_name"] = None
            logger.warning("[test_case] Attachment failed — continuing pipeline")

    except Exception as e:
        logger.error("[test_case] Attachment error: %s", str(e))
        state["errors"].append({
            "agent": "test_case",
            "error": f"TC attachment: {str(e)}",
        })
        state["tc_attachment_name"] = None

    return state
