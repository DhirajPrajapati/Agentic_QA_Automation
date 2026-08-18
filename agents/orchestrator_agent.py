"""
orchestrator_agent — Fetches the Jira ticket and Confluence context into state.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import logging

from graph.state import QAState
from tools.chromadb_client import query_past_failures
from tools.confluence_client import get_page_by_id, resolve_page_ids
from tools.jira_client import get_ticket

logger = logging.getLogger(__name__)

_KNOWN_USER_TYPES = ["investor", "distributor", "employee"]
_KNOWN_MODULES = ["login", "dashboard", "redemption", "additional-purchase"]


def _resolve_module(labels: list[str]) -> str:
    """Build a 'user_type/module' identifier from Jira labels, for ChromaDB."""
    user_type = next((u for u in _KNOWN_USER_TYPES if u in labels), "unknown")
    module = next((m for m in _KNOWN_MODULES if m in labels), "unknown")
    return f"{user_type}/{module}"


def orchestrator_node(state: QAState) -> QAState:
    """Fetch the Jira ticket and its Confluence module context into state."""
    try:
        jira_data = get_ticket(state["jira_id"])
        logger.info(
            "[orchestrator] Fetching ticket: %s — %s",
            state["jira_id"],
            jira_data.get("fields", {}).get("summary"),
        )

        labels = jira_data.get("fields", {}).get("labels", [])
        page_ids = resolve_page_ids(labels)
        pages = [get_page_by_id(page_id) for page_id in page_ids]
        confluence_context = "\n\n".join(pages)
        logger.info(
            "[orchestrator] Fetched %d Confluence page(s), %d characters",
            len(pages),
            len(confluence_context),
        )

        module = _resolve_module(labels)
        summary = jira_data.get("fields", {}).get("summary", "")
        past_failures = query_past_failures(module, summary, n=5)
        logger.info(
            "[orchestrator] Retrieved %d past learnings from ChromaDB", len(past_failures)
        )

        state["jira_data"] = jira_data
        state["confluence_context"] = confluence_context
        state["past_failures"] = past_failures
        state["status"] = "orchestrator_complete"
        state["current_phase"] = "orchestrator"
    except Exception as e:
        logger.error("[orchestrator] Call failed: %s", str(e))
        state["errors"].append({"agent": "orchestrator", "error": str(e)})

    return state
