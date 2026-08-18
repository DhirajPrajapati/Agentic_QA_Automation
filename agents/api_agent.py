"""
api_agent — Runs API test cases via Newman (mock execution in Phase 4).
Part of: QA Orchestrator
Phase: 4
Mock-safe: yes
"""
import json
import logging
import os
import pathlib
import random
import subprocess

from graph.state import QAState

logger = logging.getLogger(__name__)


def _mock_api_results(state: QAState) -> dict:
    """Generate realistic mock Newman-style results for every API test case."""
    mock_results: dict[str, dict] = {}
    api_cases = [tc for tc in state["test_cases"] if tc["type"] == "api"]
    for tc in api_cases:
        mock_results[tc["id"]] = {
            "name": tc["flow"],
            "status": "pass",
            "response_time_ms": random.randint(180, 450),
            "status_code": 200,
            "endpoint": f"POST /api/v1/{tc['flow'].replace('_', '/')}",
        }

    neg_cases = [tc for tc in api_cases if tc["priority"] == "P2"]
    if neg_cases:
        tc = neg_cases[0]
        mock_results[tc["id"]]["status_code"] = 401
        mock_results[tc["id"]]["status"] = "pass"  # 401 was expected

    return mock_results


def _run_newman(state: QAState) -> dict:
    """Write the collection/environment to disk, run Newman, and parse its report."""
    collection_path = pathlib.Path("outputs/collections") / f"temp_{state['jira_id']}.json"
    collection_path.parent.mkdir(parents=True, exist_ok=True)
    collection_path.write_text(json.dumps(state["api_collection"], indent=2))

    env_data = {
        "id": "uat-env",
        "name": "UAT",
        "values": [
            {"key": "base_url", "value": os.getenv("UAT_BASE_URL"), "enabled": True},
            {"key": "auth_token", "value": "", "enabled": True},
        ],
    }
    env_path = pathlib.Path("outputs/collections") / f"temp_{state['jira_id']}_env.json"
    env_path.write_text(json.dumps(env_data))

    report_path = pathlib.Path("outputs/reports") / f"{state['jira_id']}_api_report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    result = subprocess.run(
        [
            "newman",
            "run",
            str(collection_path),
            "--environment",
            str(env_path),
            "--reporters",
            "json",
            "--reporter-json-export",
            str(report_path),
            "--timeout-request",
            "10000",
        ],
        capture_output=True,
        text=True,
    )
    logger.info("[api_agent] Newman exit code: %d", result.returncode)
    if result.stderr:
        logger.warning("[api_agent] Newman stderr: %s", result.stderr[:200])

    try:
        report = json.loads(report_path.read_text())
        executions = report.get("run", {}).get("executions", [])
        api_results = {}
        for i, ex in enumerate(executions):
            tc_id = f"API-{i + 1:03d}"
            response = ex.get("response", {})
            assertions = ex.get("assertions", [])
            failed_assertions = [a for a in assertions if a.get("error")]
            api_results[tc_id] = {
                "name": ex.get("item", {}).get("name", "Unknown"),
                "status": "fail" if failed_assertions else "pass",
                "status_code": response.get("code", 0),
                "response_time_ms": response.get("responseTime", 0),
                "failures": [a["error"]["message"] for a in failed_assertions],
            }
        return api_results
    except Exception as e:
        logger.error("[api_agent] Failed to parse Newman report: %s", str(e))
        state["errors"].append({"agent": "api_agent", "error": str(e)})
        return {}


def api_node(state: QAState) -> QAState:
    """Run (or, in mock mode, mock-run) every API test case via Newman."""
    if state.get("skip_api", False):
        logger.info("[api_agent] Skipping API tests — FE-only ticket")
        state["api_results"] = {}
        state["status"] = "api_skipped"
        return state

    try:
        use_mock = os.getenv("USE_MOCK", "true").lower() == "true"
        if use_mock:
            api_results = _mock_api_results(state)
            logger.info("[api_agent] Mock API results: %d requests", len(api_results))
        else:
            api_results = _run_newman(state)
            logger.info(
                "[api_agent] API results: %d requests, %d failed",
                len(api_results),
                sum(1 for r in api_results.values() if r["status"] == "fail"),
            )

        state["api_results"] = api_results
        state["status"] = "api_complete"
    except Exception as e:
        logger.error("[api_agent] Call failed: %s", str(e))
        state["errors"].append({"agent": "api_agent", "error": str(e)})
        state["api_results"] = {}

    return state
