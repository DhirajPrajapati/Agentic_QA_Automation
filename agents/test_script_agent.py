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

# Fully autonomous — no human approval gate. The {recording}/{test_cases}/
# {selector_hints} placeholders are substituted below; every other {...}
# (e.g. {jira_id}, {test_case_id}) is literal instructional text showing the
# LLM the metadata-comment-block pattern to follow using the real values
# already present in the {test_cases} JSON — do not str.format() this
# template as a whole.
UI_WITH_RECORDING_PROMPT = """You are a senior QA automation engineer.
You are part of a fully autonomous QA pipeline.

Generate a complete Playwright Python test file using this recording
as the selector baseline. Do not invent selectors not in the recording.

Recording (real selectors from portal DOM):
{recording}

Test cases to implement (all Auto-Generated — no approval gate):
{test_cases}

MANDATORY rules from our Playwright standards:

Locator priority order (follow strictly):
1. page.get_by_role(...)
2. page.get_by_label(...)
3. page.get_by_placeholder(...)
4. page.get_by_test_id(...) when available
5. CSS/XPath only if above are unavailable

Assertions — use web-first assertions:
- expect(page).to_have_url(...)
- expect(locator).to_have_text(...)
- expect(locator).to_be_visible()
- expect(locator).to_be_enabled()
Assert meaningful business outcomes, not just element presence.

Structure — Arrange Act Assert:
# Arrange — setup and navigation
# Act — user actions
# Assert — verify outcomes

Metadata comment block — add at top of EACH test function:
# Jira Id: {jira_id}
# Test Case ID: {test_case_id}
# Module: {module}
# Sub-Module: {sub_module}
# Priority: {priority}
# Type: {type}
# Tags: {tags}
# Automation Status: Auto-Generated
# Test Case Description: {description}
# Preconditions:
#   {preconditions}
# Expected Results:
#   {expected_results}

Tagging — use pytest marks:
@pytest.mark.smoke for Smoke type
@pytest.mark.functional for Functional type
@pytest.mark.regression for Regression type

Test independence:
Each test must be independently executable.
Do not rely on execution order.
Use test fixtures for shared state like login.

Do NOT use arbitrary time.sleep() or waitForTimeout.
Use Playwright auto-waiting and explicit state assertions.

Output: Complete Python Playwright file only.
No explanation. No markdown. Raw Python code only."""

UI_WITHOUT_RECORDING_PROMPT = """You are a senior QA automation engineer.
Generate a Playwright Python test file using these UI element hints.

# WARNING: No recording available. Selectors based on documentation hints.
# Prefer getByRole > getByLabel > getByPlaceholder > getByTestId > CSS

UI element hints from Confluence Section 8:
{selector_hints}

Test cases:
{test_cases}

Apply same Playwright standards as always:
- Arrange Act Assert structure
- Web-first assertions only
- Metadata comment block per test function
- pytest marks: @pytest.mark.smoke / functional / regression
- Each test independently executable
- No time.sleep() — use Playwright auto-waiting

Output: Complete Python Playwright file only. Raw code only."""


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
    content = UI_WITH_RECORDING_PROMPT.replace(
        "{recording}", recording_content
    ).replace("{test_cases}", json.dumps(ui_test_cases))
    return [{"role": "user", "content": content}]


def _build_ui_prompt_without_recording(
    selector_hints: str, ui_test_cases: list[dict]
) -> list[dict[str, str]]:
    content = UI_WITHOUT_RECORDING_PROMPT.replace(
        "{selector_hints}", selector_hints
    ).replace("{test_cases}", json.dumps(ui_test_cases))
    return [{"role": "user", "content": content}]


def _generate_ui_script(state: QAState, user_type: str, module: str) -> str:
    """Generate the Playwright UI script, from a recording when one exists."""
    recording = load_recording(user_type, module)
    # The autonomous test_case schema no longer distinguishes ui/api cases
    # (its "type" field means Smoke/Functional/Regression) — every generated
    # case is a UI e2e case.
    ui_test_cases = state["test_cases"]

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
    """Persist the generated script to outputs/e2e/{user_type}/{module}/{jira_id}/v1/."""
    out_dir = Path(f"outputs/e2e/{user_type}/{module}/{jira_id}/v1")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{module}_{jira_id}_001.spec.py"
    out_path.write_text(script)
    logger.info("[test_script] UI script saved: %s", out_path)
    return out_path


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
    # The autonomous test_case schema no longer distinguishes ui/api cases —
    # every generated case is a UI e2e case, so there is nothing to enhance
    # the collection with beyond the negative-variant pass below.
    api_test_cases: list[dict] = []
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
        _save_script(user_type, module, state["jira_id"], script)
        state["ui_scripts"] = script

        if state.get("api_collection") is None:
            state["api_collection"] = _generate_api_collection(state, user_type, module)

        state["status"] = "scripts_ready"
        state["current_phase"] = "test_script"
    except Exception as e:
        logger.error("[test_script] Call failed: %s", str(e))
        state["errors"].append({"agent": "test_script", "error": str(e)})

    return state
