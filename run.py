"""
run — CLI entry point for the QA Orchestrator pipeline.
Part of: QA Orchestrator
Phase: 4
Mock-safe: yes
"""
import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from graph.graph_builder import build_graph
from graph.state import create_initial_state

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def find_newest_script(jira_id: str) -> Optional[Path]:
    """Find the most recently written outputs/scripts/*_{jira_id}.py file.

    Multiple stale files can match the same jira_id across runs (e.g. the
    resolved module changed) — the newest one is always the one this run
    (or the most recent run) just wrote.
    """
    script_files = list(Path("outputs/scripts").glob(f"*_{jira_id}.py"))
    if not script_files:
        return None
    return max(script_files, key=lambda p: p.stat().st_mtime)


def main() -> None:
    """Parse --jira, run the pipeline, and print the generated test cases."""
    parser = argparse.ArgumentParser(description="QA Orchestrator")
    parser.add_argument("--jira", required=True, help="Jira ticket id, e.g. PROJ-123")
    args = parser.parse_args()

    graph = build_graph()
    initial_state = create_initial_state(args.jira)
    final_state = graph.invoke(initial_state)

    print(json.dumps(final_state["test_cases"], indent=2))
    print(f"Generated {len(final_state['test_cases'])} test cases for {args.jira}")

    ui_results = final_state.get("ui_results") or {}
    if ui_results:
        counts = {"pass": 0, "healed": 0, "fail": 0}
        for result in ui_results.values():
            counts[result["status"]] = counts.get(result["status"], 0) + 1
        print(
            f"UI Results: {counts['pass']} pass | {counts['healed']} healed | "
            f"{counts['fail']} fail"
        )

    newest_script = find_newest_script(args.jira)
    if newest_script is not None:
        print(f"Script saved to: {newest_script}")

    api_results = final_state.get("api_results") or {}
    genuine_ui_failures = [r for r in ui_results.values() if r.get("status") == "fail"]
    genuine_api_failures = [r for r in api_results.values() if r.get("status") == "fail"]

    total_failures = len(genuine_ui_failures) + len(genuine_api_failures)
    if total_failures > 0:
        logger.warning("Run completed with %d failure(s)", total_failures)
        sys.exit(1)
    else:
        logger.info("Run completed — all tests passed or healed")
        sys.exit(0)


if __name__ == "__main__":
    main()
