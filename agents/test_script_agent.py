"""
test_script_agent — Generates a Playwright UI script and a Postman API
collection from the recorded baseline (or Confluence hints) plus test cases.
Part of: QA Orchestrator
Phase: 2
Mock-safe: yes
"""
import copy
import json
import logging
from pathlib import Path

from graph.state import QAState
from tools.collection_loader import load_collection
from tools.llm_client import invoke_with_retry
from tools.recording_loader import load_recording

logger = logging.getLogger(__name__)

_KNOWN_USER_TYPES = ["investor", "distributor", "employee"]
_KNOWN_MODULES = ["login", "dashboard", "redemption"]

_WARNING_COMMENT = (
    "# WARNING: Generated without recording. Selectors may need manual verification."
)

_MINIMAL_API_COLLECTION_STUB = {
    "info": {
        "name": "stub",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    },
    "item": [],
}


def _extract_user_type_and_module(labels: list[str]) -> tuple[str | None, str | None]:
    """Pick the first known user_type and module present in the Jira labels."""
    user_type = next((u for u in _KNOWN_USER_TYPES if u in labels), None)
    module = next((m for m in _KNOWN_MODULES if m in labels), None)
    return user_type, module


def _extract_selector_hints(confluence_context: str) -> str:
    """Extract the UI Element Hints section (Section 8) from Confluence text."""
    start_marker = "8. UI ELEMENT HINTS"
    end_marker = "9. TEST DATA"
    start = confluence_context.find(start_marker)
    if start == -1:
        return confluence_context
    end = confluence_context.find(end_marker, start)
    return confluence_context[start:end] if end != -1 else confluence_context[start:]


def _build_ui_prompt_with_recording(
    recording_content: str, ui_test_cases: list[dict]
) -> list[dict[str, str]]:
    content = (
        "You are a QA automation engineer. Given this Playwright recording of a\n"
        "happy path flow, add the following to it without changing existing selectors:\n"
        "1. expect() assertions after each navigation step\n"
        "2. Separate test functions for each negative test case in the test_cases list\n"
        "   using the SAME selectors as the recording, different test data\n"
        "3. Add explicit page.wait_for_load_state() where needed\n"
        f"Recording:\n{recording_content}\n"
        f"Test cases:\n{json.dumps(ui_test_cases)}\n"
        "Output: Complete Python Playwright file only. No explanation."
    )
    return [{"role": "user", "content": content}]


def _build_ui_prompt_without_recording(
    selector_hints: str, ui_test_cases: list[dict]
) -> list[dict[str, str]]:
    content = (
        "Generate a Playwright Python test file for these test cases.\n"
        f"Use these UI element hints from the portal knowledge base:\n{selector_hints}\n"
        f"Test cases: {json.dumps(ui_test_cases)}\n"
        "WARNING: No recording available. Add comment at top of file:\n"
        f"{_WARNING_COMMENT}"
    )
    return [{"role": "user", "content": content}]


def _generate_ui_script(state: QAState, user_type: str, module: str) -> str:
    """Generate the Playwright UI script, from a recording when one exists."""
    recording = load_recording(user_type, module)
    ui_test_cases = [tc for tc in state["test_cases"] if tc.get("type") == "ui"]

    if recording is not None:
        logger.info(
            "[test_script] Loaded recording: recordings/%s/%s_happy_path.py",
            user_type,
            module,
        )
        messages = _build_ui_prompt_with_recording(recording, ui_test_cases)
        return invoke_with_retry(messages=messages, agent_type="test_script_ui")

    logger.info(
        "[test_script] No recording found for %s/%s — using Confluence hints",
        user_type,
        module,
    )
    hints = _extract_selector_hints(state["confluence_context"])
    messages = _build_ui_prompt_without_recording(hints, ui_test_cases)
    script = invoke_with_retry(messages=messages, agent_type="test_script_ui")
    return f"{_WARNING_COMMENT}\n{script}"


def _save_script(user_type: str, module: str, jira_id: str, script: str) -> Path:
    """Persist the generated script to outputs/scripts/."""
    output_dir = Path("outputs/scripts")
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{user_type}_{module}_{jira_id}.py"
    path.write_text(script)
    return path


def _build_api_prompt(collection: dict, api_test_cases: list[dict]) -> list[dict[str, str]]:
    content = (
        "Given this Postman collection, add negative test cases for each request.\n"
        "For each existing request, add 2-3 negative variants:\n"
        "- Invalid/missing required fields\n"
        "- Wrong auth token\n"
        "- Boundary values\n"
        f"Collection: {json.dumps(collection)}\n"
        f"API test cases from test plan: {json.dumps(api_test_cases)}\n"
        "Output: Complete valid Postman collection JSON only."
    )
    return [{"role": "user", "content": content}]


def _generate_api_collection(state: QAState, user_type: str, module: str) -> dict:
    """Enhance the Postman collection with negative cases, or fall back to a stub."""
    collection = load_collection(user_type, module)
    if collection is None:
        logger.info(
            "[test_script] No Postman collection found for %s/%s — using stub",
            user_type,
            module,
        )
        return copy.deepcopy(_MINIMAL_API_COLLECTION_STUB)

    logger.info(
        "[test_script] Loaded Postman collection: postman_collections/%s/%s.postman_collection.json",
        user_type,
        module,
    )
    api_test_cases = [tc for tc in state["test_cases"] if tc.get("type") == "api"]
    messages = _build_api_prompt(collection, api_test_cases)
    raw = invoke_with_retry(messages=messages, agent_type="test_script_api")
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error("[test_script] Failed to parse LLM JSON for API collection: %s", str(e))
        return collection


def test_script_node(state: QAState) -> QAState:
    """Generate the UI script and API collection for the resolved user_type/module."""
    try:
        labels = state["jira_data"].get("fields", {}).get("labels", [])
        user_type, module = _extract_user_type_and_module(labels)

        if user_type is None or module is None:
            logger.warning(
                "[test_script] Could not determine user_type/module from labels: %s", labels
            )
            state["ui_scripts"] = None
            if state.get("api_collection") is None:
                state["api_collection"] = copy.deepcopy(_MINIMAL_API_COLLECTION_STUB)
            state["status"] = "scripts_ready"
            state["current_phase"] = "test_script"
            return state

        script = _generate_ui_script(state, user_type, module)
        script_path = _save_script(user_type, module, state["jira_id"], script)
        logger.info("[test_script] Saved script: %s", script_path)
        state["ui_scripts"] = script

        if state.get("api_collection") is None:
            state["api_collection"] = _generate_api_collection(state, user_type, module)

        state["status"] = "scripts_ready"
        state["current_phase"] = "test_script"
    except Exception as e:
        logger.error("[test_script] Call failed: %s", str(e))
        state["errors"].append({"agent": "test_script", "error": str(e)})

    return state
