"""
playwright_agent — Runs UI test cases (mock execution in Phase 2/3).
Part of: QA Orchestrator
Phase: 3
Mock-safe: yes
"""
import logging
import os
import random

from graph.state import QAState
from tools.chromadb_client import get_healed_selectors, write_healed_selector

logger = logging.getLogger(__name__)

_STATUS_EMOJI = {"pass": "✅", "healed": "⚡", "fail": "❌"}

_KNOWN_USER_TYPES = ["investor", "distributor", "employee"]
_KNOWN_MODULES = ["login", "dashboard", "redemption", "additional-purchase"]


def _resolve_module_id(labels: list[str]) -> str:
    """Build a 'user_type/module' identifier from Jira labels, for ChromaDB."""
    user_type = next((u for u in _KNOWN_USER_TYPES if u in labels), "unknown")
    module = next((m for m in _KNOWN_MODULES if m in labels), "unknown")
    return f"{user_type}/{module}"


def _write_healed_selector(original: str, healed: str, module: str, element: str) -> None:
    """Write a newly healed selector to ChromaDB."""
    try:
        write_healed_selector(original, healed, module, element)
        logger.info("[playwright] New healing written to ChromaDB")
    except Exception as e:
        logger.error("[playwright] Failed to write healed selector to ChromaDB: %s", str(e))


def _simulate_test_case(tc: dict, module_id: str, healed_map: dict[str, str]) -> dict:
    """Simulate one UI test case execution with a 70/20/10 pass/healed/fail split."""
    status = random.choices(["pass", "healed", "fail"], weights=[70, 20, 10])[0]
    # "flow" is the legacy schema key; the autonomous schema has no flow field,
    # so fall back to module (or test_case_id) to name the simulated selector.
    flow = tc.get("flow") or tc.get("module") or tc.get("test_case_id", "unknown_flow")

    if status == "pass":
        return {"status": "pass", "duration_ms": random.randint(1200, 3500)}

    if status == "healed":
        original_selector = f".btn-{flow.replace('_', '-')}"

        if original_selector in healed_map:
            healed_selector = healed_map[original_selector]
            logger.info("[playwright] Using previously healed selector from memory")
        else:
            healed_selector = f"button:has-text('{flow.replace('_', ' ').title()}')"
            _write_healed_selector(original_selector, healed_selector, module_id, flow)

        return {
            "status": "healed",
            "duration_ms": random.randint(3000, 5500),
            "original_selector": original_selector,
            "healed_selector": healed_selector,
        }

    tc_id = tc.get("test_case_id") or tc.get("id", "unknown")
    return {
        "status": "fail",
        "error": f"Selector not found: .{flow}-container",
        "screenshot_path": f"outputs/screenshots/{tc_id}_fail.png",
    }


def playwright_node(state: QAState) -> QAState:
    """Run (or, in Phase 2/3, mock-run) every UI test case and record results."""
    try:
        use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
        if not use_mock:
            # TODO Phase 5: Implement real browser execution here.
            logger.warning(
                "[playwright] USE_MOCK=false but real execution is not implemented "
                "until Phase 5 — returning mock results"
            )

        labels = state["jira_data"].get("fields", {}).get("labels", [])
        module_id = _resolve_module_id(labels)

        healed_map = get_healed_selectors(module_id)
        logger.info("[playwright] Loaded %d previously healed selectors", len(healed_map))

        # The autonomous test_case schema no longer distinguishes ui/api cases
        # (its "type" field means Smoke/Functional/Regression) — every
        # generated case is a UI e2e case.
        ui_test_cases = state["test_cases"]
        ui_results: dict[str, dict] = {}
        for tc in ui_test_cases:
            tc_id = tc.get("test_case_id") or tc.get("id", "unknown")
            result = _simulate_test_case(tc, module_id, healed_map)
            ui_results[tc_id] = result
            logger.info(
                "[playwright] %s %s → %s %s",
                tc_id,
                tc.get("flow", ""),
                result["status"].upper(),
                _STATUS_EMOJI[result["status"]],
            )

        counts = {"pass": 0, "healed": 0, "fail": 0}
        for result in ui_results.values():
            counts[result["status"]] += 1
        logger.info(
            "[playwright] Results: %d pass, %d healed, %d fail",
            counts["pass"],
            counts["healed"],
            counts["fail"],
        )

        state["ui_results"] = ui_results
        state["status"] = "ui_complete"
        state["current_phase"] = "playwright"
    except Exception as e:
        logger.error("[playwright] Call failed: %s", str(e))
        state["errors"].append({"agent": "playwright", "error": str(e)})

    return state
