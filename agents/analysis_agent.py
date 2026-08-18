"""
analysis_agent — Determines test scope: flows, risk areas, user types, skip_api.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import json
import logging

from graph.state import QAState
from tools.llm_client import invoke_with_retry

logger = logging.getLogger(__name__)

_FRONTEND_ONLY_LABELS = {"frontend", "ui", "css", "layout"}


def _build_prompt(state: QAState) -> list[dict[str, str]]:
    """Build the analysis prompt from jira_data, confluence_context, past_failures."""
    fields = state["jira_data"].get("fields", {})
    summary = fields.get("summary", "")
    acceptance_criteria = fields.get("acceptance_criteria", [])
    confluence_excerpt = state["confluence_context"][:3000]
    past_failures = state["past_failures"]

    content = (
        f"Jira summary: {summary}\n"
        f"Acceptance criteria: {acceptance_criteria}\n"
        f"Confluence context:\n{confluence_excerpt}\n"
        f"Past failures: {past_failures}\n\n"
        "Output ONLY valid JSON, no markdown, no explanation. Schema:\n"
        '{"flows_to_test": [...], "skip_api": bool, '
        '"risk_areas": [...], "user_types_in_scope": [...]}'
    )
    return [{"role": "user", "content": content}]


def _determine_skip_api(labels: list[str]) -> bool:
    """True when every label is a frontend-only term (no backend/API scope)."""
    if not labels:
        return False
    return all(label in _FRONTEND_ONLY_LABELS for label in labels)


def analysis_node(state: QAState) -> QAState:
    """Determine flows to test, risk areas, user types, and skip_api."""
    try:
        messages = _build_prompt(state)
        raw = invoke_with_retry(messages=messages, agent_type="analysis")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error("[analysis] Failed to parse LLM JSON output: %s", str(e))
            parsed = {
                "flows_to_test": [],
                "risk_areas": [],
                "user_types_in_scope": [],
            }

        labels = state["jira_data"].get("fields", {}).get("labels", [])

        state["flows_to_test"] = parsed.get("flows_to_test", [])
        state["skip_api"] = _determine_skip_api(labels)
        state["risk_areas"] = parsed.get("risk_areas", [])
        state["user_types_in_scope"] = parsed.get("user_types_in_scope", [])
        state["status"] = "analysis_complete"
        state["current_phase"] = "analysis"

        logger.info(
            "[analysis] Flows: %s | skip_api=%s | risk_areas=%d",
            state["flows_to_test"],
            state["skip_api"],
            len(state["risk_areas"]),
        )
    except Exception as e:
        logger.error("[analysis] Call failed: %s", str(e))
        state["errors"].append({"agent": "analysis", "error": str(e)})

    return state
