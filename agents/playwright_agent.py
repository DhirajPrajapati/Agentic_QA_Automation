"""
playwright_agent — Runs UI test cases (mock Phase 2/3, real browser Phase 5).
Part of: QA Orchestrator
Phase: 5
Mock-safe: yes
"""
import json
import logging
import os
import random
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from graph.state import QAState
from tools.chromadb_client import get_healed_selectors, write_healed_selector
from tools.llm_client import invoke_with_retry

logger = logging.getLogger(__name__)

_STATUS_EMOJI = {"pass": "✅", "healed": "⚡", "fail": "❌"}

_KNOWN_USER_TYPES = ["investor", "distributor", "employee"]
_KNOWN_MODULES = ["login", "dashboard", "redemption", "additional-purchase"]

MAX_HEAL_ATTEMPTS = 3


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


# ── Mock execution ─────────────────────────────────────────────────────────────

def _simulate_test_case(tc: dict, module_id: str, healed_map: dict[str, str]) -> dict:
    """Simulate one UI test case execution with a 70/20/10 pass/healed/fail split."""
    status = random.choices(["pass", "healed", "fail"], weights=[70, 20, 10])[0]
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


def _run_mock_tests(state: QAState, module_id: str, healed_map: dict[str, str]) -> dict:
    """Simulate every test case in mock mode and return ui_results dict."""
    ui_results: dict[str, dict] = {}
    for tc in state["test_cases"]:
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
    return ui_results


# ── Real execution ─────────────────────────────────────────────────────────────

def _find_spec_file(jira_id: str) -> Optional[Path]:
    """Locate the most recently generated spec file for this jira_id."""
    files = list(Path("outputs/e2e").rglob(f"*_{jira_id}_*.spec.py"))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def _extract_selector_section(confluence_context: str) -> str:
    """Extract Section 8 (UI Element Hints) from the Confluence page text."""
    start = confluence_context.find("8. UI ELEMENT HINTS")
    end = confluence_context.find("9. TEST DATA", start) if start != -1 else -1
    if start == -1:
        return confluence_context[:1500]
    return confluence_context[start:end] if end != -1 else confluence_context[start:]


def _run_pytest(script_path: Path, jira_id: str) -> dict:
    """Execute the spec file with pytest-playwright; return {test_name: result_dict}."""
    report_path = Path("outputs/reports") / f"{jira_id}_playwright_report.json"
    screenshot_dir = Path("outputs/screenshots") / jira_id
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    proc = subprocess.run(
        [
            sys.executable, "-m", "pytest",
            str(script_path),
            "--browser", "chromium",
            "--screenshot", "only-on-failure",
            "--output", str(screenshot_dir),
            "--json-report",
            f"--json-report-file={report_path}",
            "-v",
            "--timeout=30",
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    logger.info("[playwright] pytest exit code: %d", proc.returncode)
    if proc.stderr:
        logger.debug("[playwright] pytest stderr: %s", proc.stderr[:200])

    test_results: dict[str, dict] = {}
    try:
        report = json.loads(report_path.read_text())
        for test in report.get("tests", []):
            tc_id = test["nodeid"].split("::")[-1]
            outcome = test["outcome"]
            if outcome == "passed":
                entry: dict = {
                    "status": "pass",
                    "duration_ms": int(test.get("duration", 0) * 1000),
                }
            else:
                longrepr = (test.get("call") or {}).get("longrepr", "") or ""
                entry = {"status": "fail", "error": str(longrepr)[:300]}
                screenshots = list(screenshot_dir.glob(f"*{tc_id}*.png"))
                if screenshots:
                    entry["screenshot_path"] = str(screenshots[0])
            test_results[tc_id] = entry
            logger.info(
                "[playwright] %s → %s %s",
                tc_id,
                entry["status"].upper(),
                _STATUS_EMOJI.get(entry["status"], ""),
            )
    except Exception as e:
        logger.error("[playwright] Failed to parse pytest report: %s", str(e))

    return test_results


def _extract_failed_selector(error_text: str) -> Optional[str]:
    """Extract the CSS/text selector that caused a Playwright test failure."""
    patterns = [
        r'locator\([\'"](.+?)[\'"]\)',
        r"selector ['\"](.+?)['\"]",
        r"fill\(['\"](.+?)['\"]\s*,",
        r"click\(['\"](.+?)['\"]\)",
        r"get_by_placeholder\(['\"](.+?)['\"]\)",
    ]
    for pattern in patterns:
        match = re.search(pattern, error_text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None


def _build_heal_prompt(
    failed_selector: str,
    error_text: str,
    confluence_hints: str,
    past_heals: list[str],
) -> list[dict[str, str]]:
    """Build the LLM prompt asking for alternative selector candidates."""
    content = (
        "A Playwright selector failed during automated test execution.\n\n"
        f"Failed selector: {failed_selector}\n"
        f"Error: {error_text[:300]}\n\n"
        f"Confluence UI element hints:\n{confluence_hints[:1500]}\n\n"
        f"Previously successful healed selectors for this module:\n{past_heals}\n\n"
        f"Suggest {MAX_HEAL_ATTEMPTS} alternative selectors in order of confidence.\n"
        "Prefer: getByRole > getByLabel > getByPlaceholder > CSS.\n"
        "Output ONLY valid JSON, no explanation. Schema:\n"
        '{"candidate_selectors": ["selector1", "selector2", "selector3"]}'
    )
    return [{"role": "user", "content": content}]


def _heal_test(
    script_path: Path,
    tc_id: str,
    failed_selector: str,
    error_text: str,
    confluence_hints: str,
    past_heals: list[str],
    module_id: str,
) -> tuple[str, Optional[str]]:
    """Try LLM-suggested selectors until one passes. Returns (status, healed_selector)."""
    messages = _build_heal_prompt(failed_selector, error_text, confluence_hints, past_heals)
    try:
        raw = invoke_with_retry(messages=messages, agent_type="self_heal")
        candidates: list[str] = json.loads(raw).get("candidate_selectors", [])
    except Exception as e:
        logger.error("[playwright] Heal prompt failed: %s", str(e))
        return "fail", None

    original_content = script_path.read_text()

    for candidate in candidates[:MAX_HEAL_ATTEMPTS]:
        logger.warning("[playwright] Self-healing: trying %s", candidate)
        patched = original_content.replace(
            f'"{failed_selector}"', f'"{candidate}"'
        ).replace(
            f"'{failed_selector}'", f"'{candidate}'"
        )
        if patched == original_content:
            logger.warning("[playwright] Selector not found in script: %s", failed_selector)
            continue

        script_path.write_text(patched)
        probe = subprocess.run(
            [
                sys.executable, "-m", "pytest",
                str(script_path),
                "--browser", "chromium",
                "-k", tc_id,
                "-q",
                "--no-header",
                "--timeout=30",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if probe.returncode == 0:
            logger.info("[playwright] Self-heal succeeded: %s → %s", failed_selector, candidate)
            _write_healed_selector(failed_selector, candidate, module_id, tc_id)
            return "healed", candidate

        script_path.write_text(original_content)

    script_path.write_text(original_content)
    return "fail", None


def _run_real_tests(state: QAState, module_id: str) -> dict:
    """Run the spec file with real Playwright and apply self-healing on selector failures."""
    jira_id = state["jira_id"]
    script_path = _find_spec_file(jira_id)
    if script_path is None:
        logger.warning("[playwright] No spec file found for %s — no UI results", jira_id)
        return {}

    logger.info("[playwright] Running spec: %s", script_path)
    results = _run_pytest(script_path, jira_id)

    confluence_hints = _extract_selector_section(state.get("confluence_context", ""))
    healed_map = get_healed_selectors(module_id)
    past_heals = list(healed_map.values())

    for tc_id, result in results.items():
        if result["status"] != "fail":
            continue
        error_text = result.get("error", "")
        failed_selector = _extract_failed_selector(error_text)
        if not failed_selector:
            logger.warning("[playwright] No extractable selector from error in %s", tc_id)
            continue
        logger.warning("[playwright] Self-healing: %s", failed_selector)
        status, healed_selector = _heal_test(
            script_path=script_path,
            tc_id=tc_id,
            failed_selector=failed_selector,
            error_text=error_text,
            confluence_hints=confluence_hints,
            past_heals=past_heals,
            module_id=module_id,
        )
        results[tc_id]["status"] = status
        if healed_selector:
            results[tc_id]["original_selector"] = failed_selector
            results[tc_id]["healed_selector"] = healed_selector

    return results


# ── Graph node ─────────────────────────────────────────────────────────────────

def playwright_node(state: QAState) -> QAState:
    """Run UI test cases — mock simulation (Phase 2/3) or real Playwright (Phase 5)."""
    try:
        use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
        labels = state["jira_data"].get("fields", {}).get("labels", [])
        module_id = _resolve_module_id(labels)

        if use_mock:
            healed_map = get_healed_selectors(module_id)
            logger.info("[playwright] Loaded %d previously healed selectors", len(healed_map))
            ui_results = _run_mock_tests(state, module_id, healed_map)
        else:
            logger.info("[playwright] USE_MOCK=false — running real Playwright execution")
            ui_results = _run_real_tests(state, module_id)

        counts = {"pass": 0, "healed": 0, "fail": 0}
        for result in ui_results.values():
            counts[result["status"]] = counts.get(result["status"], 0) + 1
        logger.info(
            "[playwright] Results: %d pass, %d healed, %d fail",
            counts["pass"], counts["healed"], counts["fail"],
        )

        state["ui_results"] = ui_results
        state["status"] = "ui_complete"
        state["current_phase"] = "playwright"
    except Exception as e:
        logger.error("[playwright] Call failed: %s", str(e))
        state["errors"].append({"agent": "playwright", "error": str(e)})

    return state
