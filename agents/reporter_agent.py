"""
reporter_agent — Builds the Jira comment + email report, writes a ChromaDB learning.
Part of: QA Orchestrator
Phase: 4
Mock-safe: yes
"""
import logging
import os
from datetime import datetime
from typing import Optional

from graph.state import QAState
from tools.chromadb_client import write_learning
from tools.jira_client import post_comment

logger = logging.getLogger(__name__)

_KNOWN_USER_TYPES = ["investor", "distributor", "employee"]
_KNOWN_MODULES = ["login", "dashboard", "redemption", "additional-purchase"]


def _resolve_module(labels: list[str]) -> str:
    """Build a 'user_type/module' identifier from Jira labels, for ChromaDB."""
    user_type = next((u for u in _KNOWN_USER_TYPES if u in labels), "unknown")
    module = next((m for m in _KNOWN_MODULES if m in labels), "unknown")
    return f"{user_type}/{module}"


def _build_reflection_doc(state: QAState, ui_results: dict, failures: list, healed: list) -> str:
    """Build the free-text reflection document written to ChromaDB after each run."""
    reflection_parts = []
    if failures:
        reflection_parts.append(f"Failures: {', '.join(failures)}.")
    if healed:
        reflection_parts.append(f"Auto-healed: {', '.join(healed)}.")
    for tc_id, result in ui_results.items():
        if result["status"] == "healed":
            reflection_parts.append(
                f"Selector healing in {state['jira_data']['fields']['labels']}: "
                f"TC {tc_id} was healed successfully."
            )
    risk = state.get("risk_areas", [])
    if risk:
        reflection_parts.append(f"Known risk areas: {'; '.join(risk)}.")

    return f"Test run for {state['jira_id']}. " + " ".join(reflection_parts)


def _build_jira_comment(
    jira_id: str,
    tc_map: dict,
    ui_results: dict,
    api_results: dict,
    ui_pass: int,
    ui_healed: int,
    ui_fail: int,
    api_pass: int,
    api_fail: int,
    errors: list,
    tc_attachment: Optional[str],
) -> str:
    """Build the formatted Jira comment summarizing the full run."""
    comment_lines = [
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"🤖 Agentic QA Report — {jira_id}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "",
        f"UI Tests:  {ui_pass} pass | {ui_healed} healed | {ui_fail} fail",
    ]
    if api_results:
        comment_lines.append(f"API Tests: {api_pass} pass | {api_fail} fail")
    comment_lines.append("")

    for tc_id, result in ui_results.items():
        tc = tc_map.get(tc_id, {})
        flow = tc.get("flow", tc_id)
        status = result["status"]
        if status == "pass":
            icon = "✅"
            detail = f"({result.get('duration_ms', 0)}ms)"
        elif status == "healed":
            icon = "⚡"
            orig = result.get("original_selector", "unknown")
            fixed = result.get("healed_selector", "unknown")
            detail = f"HEALED: {orig} → {fixed}"
        else:
            icon = "❌"
            detail = result.get("error", "Unknown error")
        comment_lines.append(f"{icon} {tc_id} {flow} — {detail}")

    if api_results:
        comment_lines.append("")
        comment_lines.append("API Results:")
        for req_id, result in api_results.items():
            icon = "✅" if result["status"] == "pass" else "❌"
            comment_lines.append(
                f"{icon} {result.get('name', '?')} — {result.get('status_code', '?')} "
                f"({result.get('response_time_ms', 0)}ms)"
            )

    if errors:
        comment_lines.append("")
        comment_lines.append(f"⚠️ Errors encountered: {len(errors)}")
        for err in errors[:3]:
            comment_lines.append(f"  • {err.get('agent', '?')}: {err.get('error', '?')[:80]}")

    overall = (
        "✅ All tests passed" if ui_fail == 0 and api_fail == 0 else f"❌ {ui_fail + api_fail} test(s) failed"
    )

    # Reference the attachment posted earlier by test_case_agent
    if tc_attachment:
        comment_lines.append("")
        comment_lines.append(
            f"📎 Test cases attached at start of run: {tc_attachment}"
        )

    comment_lines.append("")
    comment_lines.append(f"Overall: {overall}")
    comment_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    return "\n".join(comment_lines)


def reporter_node(state: QAState) -> QAState:
    """Build and post/mock the Jira comment + email, and write a ChromaDB learning."""
    use_mock = os.getenv("USE_MOCK", "true").lower() == "true"

    jira_id = state["jira_id"]
    test_cases = state.get("test_cases") or []
    tc_map = {tc["id"]: tc for tc in test_cases}
    ui_results = state.get("ui_results") or {}
    api_results = state.get("api_results") or {}

    ui_pass = sum(1 for r in ui_results.values() if r["status"] == "pass")
    ui_healed = sum(1 for r in ui_results.values() if r["status"] == "healed")
    ui_fail = sum(1 for r in ui_results.values() if r["status"] == "fail")
    api_pass = sum(1 for r in api_results.values() if r["status"] == "pass")
    api_fail = sum(1 for r in api_results.values() if r["status"] == "fail")

    jira_comment = _build_jira_comment(
        jira_id,
        tc_map,
        ui_results,
        api_results,
        ui_pass,
        ui_healed,
        ui_fail,
        api_pass,
        api_fail,
        state.get("errors") or [],
        state.get("tc_attachment_name"),
    )

    if use_mock:
        print("\n=== MOCK JIRA COMMENT ===")
        print(jira_comment)
        print("=========================\n")
    else:
        try:
            post_comment(jira_id, jira_comment)
            logger.info("[reporter] Jira comment posted to %s", jira_id)
        except Exception as e:
            logger.error("[reporter] Failed to post Jira comment: %s", str(e))
            state["errors"].append({"agent": "reporter", "error": str(e)})

    overall_summary = (
        "All tests passed" if ui_fail == 0 and api_fail == 0 else f"{ui_fail + api_fail} test(s) failed"
    )
    subject = f"QA Report: {jira_id} — {overall_summary}"
    email_body = (
        f"Subject: {subject}\n\n{jira_comment}\n\n"
        f"Run ID: {jira_id}\nTimestamp: {datetime.now().isoformat()}"
    )

    if use_mock:
        print("=== MOCK EMAIL ===")
        print(email_body)
        print("==================\n")
    else:
        try:
            import smtplib
            from email.mime.text import MIMEText

            msg = MIMEText(email_body)
            msg["Subject"] = subject
            msg["From"] = os.getenv("SMTP_USER")
            msg["To"] = os.getenv("EMAIL_RECIPIENTS")
            with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", 587))) as s:
                s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
                s.send_message(msg)
            logger.info("[reporter] Email sent to %s", os.getenv("EMAIL_RECIPIENTS"))
        except Exception as e:
            logger.error("[reporter] Failed to send email: %s", str(e))
            state["errors"].append({"agent": "reporter", "error": str(e)})

    try:
        failures = [k for k, v in ui_results.items() if v["status"] == "fail"]
        healed = [k for k, v in ui_results.items() if v["status"] == "healed"]
        doc = _build_reflection_doc(state, ui_results, failures, healed)

        labels = state["jira_data"].get("fields", {}).get("labels", [])
        meta = {
            "jira_id": jira_id,
            "module": _resolve_module(labels),
            "run_date": datetime.now().isoformat(),
            "total_tests": len(ui_results),
            "failures": len(failures),
            "healed": len(healed),
            "type": "run_reflection",
        }

        write_learning(doc, meta)
        logger.info("[reporter] ChromaDB learning written for %s", jira_id)
        print("=== ChromaDB: Learning written ===")
    except Exception as e:
        logger.error("[reporter] Failed to write ChromaDB learning: %s", str(e))
        state["errors"].append({"agent": "reporter", "error": str(e)})

    state["status"] = "complete"
    state["current_phase"] = "reporter"
    logger.info(
        "[reporter] Run complete for %s — UI: %d pass %d healed %d fail | API: %d pass %d fail",
        jira_id,
        ui_pass,
        ui_healed,
        ui_fail,
        api_pass,
        api_fail,
    )

    return state
