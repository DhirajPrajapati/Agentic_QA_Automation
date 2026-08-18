# Phase 4 Master Prompt
## Copy this entire prompt into Claude Chat

---

```
You are helping me build Phase 4 of the QA Orchestrator.
Phases 1, 2, and 3 are complete and passing. Read CLAUDE.md first.

## PHASE 4 SCOPE:
Goal: Full pipeline end-to-end. Newman runs API tests. Reporter prints
mock Jira comment + mock email to console. Exit code logic for GitHub Actions.

New files: agents/api_agent.py
Updated files: reporter_agent.py (full), graph_builder.py, run.py

## Task 1: agents/api_agent.py

api_node(state: QAState) -> QAState must:

STEP 1 — Skip check:
if state.get("skip_api", False):
    logger.info("[api_agent] Skipping API tests — FE-only ticket")
    state["api_results"] = {}
    state["status"] = "api_skipped"
    return state

STEP 2 — Mock mode:
if USE_MOCK:
    # Generate realistic mock Newman results
    mock_results = {}
    api_cases = [tc for tc in state["test_cases"] if tc["type"] == "api"]
    for tc in api_cases:
        mock_results[tc["id"]] = {
            "name": tc["flow"],
            "status": "pass",
            "response_time_ms": random.randint(180, 450),
            "status_code": 200,
            "endpoint": f"POST /api/v1/{tc['flow'].replace('_','/')}"
        }
    # Add one realistic failed case if there are negative cases
    neg_cases = [tc for tc in api_cases if tc["priority"] == "P2"]
    if neg_cases:
        tc = neg_cases[0]
        mock_results[tc["id"]]["status_code"] = 401
        mock_results[tc["id"]]["status"] = "pass"  # 401 was expected
    logger.info("[api_agent] Mock API results: %d requests", len(mock_results))
    state["api_results"] = mock_results
    state["status"] = "api_complete"
    return state

STEP 3 — Real Newman execution:
import subprocess, json, tempfile, pathlib

# Write collection to temp file
collection_path = pathlib.Path("outputs/collections") / f"temp_{state['jira_id']}.json"
collection_path.parent.mkdir(parents=True, exist_ok=True)
collection_path.write_text(json.dumps(state["api_collection"], indent=2))

# Write environment to temp file
env_data = {
    "id": "uat-env",
    "name": "UAT",
    "values": [
        {"key": "base_url", "value": os.getenv("UAT_BASE_URL"), "enabled": True},
        {"key": "auth_token", "value": "", "enabled": True}
    ]
}
env_path = pathlib.Path("outputs/collections") / f"temp_{state['jira_id']}_env.json"
env_path.write_text(json.dumps(env_data))

# Newman report path
report_path = pathlib.Path("outputs/reports") / f"{state['jira_id']}_api_report.json"
report_path.parent.mkdir(parents=True, exist_ok=True)

# Run Newman
result = subprocess.run(
    ["newman", "run", str(collection_path),
     "--environment", str(env_path),
     "--reporters", "json",
     "--reporter-json-export", str(report_path),
     "--timeout-request", "10000"],
    capture_output=True, text=True
)

logger.info("[api_agent] Newman exit code: %d", result.returncode)
if result.stderr:
    logger.warning("[api_agent] Newman stderr: %s", result.stderr[:200])

# Parse Newman report
api_results = {}
try:
    report = json.loads(report_path.read_text())
    executions = report.get("run", {}).get("executions", [])
    for i, ex in enumerate(executions):
        tc_id = f"API-{i+1:03d}"
        response = ex.get("response", {})
        assertions = ex.get("assertions", [])
        failed_assertions = [a for a in assertions if a.get("error")]
        api_results[tc_id] = {
            "name": ex.get("item", {}).get("name", "Unknown"),
            "status": "fail" if failed_assertions else "pass",
            "status_code": response.get("code", 0),
            "response_time_ms": response.get("responseTime", 0),
            "failures": [a["error"]["message"] for a in failed_assertions]
        }
except Exception as e:
    logger.error("[api_agent] Failed to parse Newman report: %s", str(e))
    state["errors"].append({"agent": "api_agent", "error": str(e)})
    api_results = {}

state["api_results"] = api_results
state["status"] = "api_complete"
logger.info("[api_agent] API results: %d requests, %d failed",
            len(api_results),
            sum(1 for r in api_results.values() if r["status"] == "fail"))
return state

## Task 2: agents/reporter_agent.py — Full Implementation

reporter_node(state: QAState) -> QAState must:

STEP 1 — Compile all results:
ui_results = state.get("ui_results") or {}
api_results = state.get("api_results") or {}
test_cases = state.get("test_cases") or []
jira_id = state["jira_id"]

# Build a lookup from TC id to test case details
tc_map = {tc["id"]: tc for tc in test_cases}

ui_pass   = sum(1 for r in ui_results.values() if r["status"] == "pass")
ui_healed = sum(1 for r in ui_results.values() if r["status"] == "healed")
ui_fail   = sum(1 for r in ui_results.values() if r["status"] == "fail")

api_pass  = sum(1 for r in api_results.values() if r["status"] == "pass")
api_fail  = sum(1 for r in api_results.values() if r["status"] == "fail")

STEP 2 — Build Jira comment string:
comment_lines = [
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    f"🤖 Agentic QA Report — {jira_id}",
    f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    f"",
    f"UI Tests:  {ui_pass} pass | {ui_healed} healed | {ui_fail} fail",
]
if api_results:
    comment_lines.append(f"API Tests: {api_pass} pass | {api_fail} fail")
comment_lines.append("")

# Per test case results
for tc_id, result in ui_results.items():
    tc = tc_map.get(tc_id, {})
    flow = tc.get("flow", tc_id)
    status = result["status"]
    if status == "pass":
        icon = "✅"
        detail = f"({result.get('duration_ms',0)}ms)"
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
            f"{icon} {result.get('name','?')} — {result.get('status_code','?')} "
            f"({result.get('response_time_ms',0)}ms)"
        )

if state.get("errors"):
    comment_lines.append("")
    comment_lines.append(f"⚠️ Errors encountered: {len(state['errors'])}")
    for err in state["errors"][:3]:
        comment_lines.append(f"  • {err.get('agent','?')}: {err.get('error','?')[:80]}")

overall = "✅ All tests passed" if ui_fail == 0 and api_fail == 0 else f"❌ {ui_fail+api_fail} test(s) failed"
comment_lines.append("")
comment_lines.append(f"Overall: {overall}")
comment_lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

jira_comment = "\n".join(comment_lines)

STEP 3 — Post or mock Jira comment:
if USE_MOCK:
    print("\n=== MOCK JIRA COMMENT ===")
    print(jira_comment)
    print("=========================\n")
else:
    try:
        from tools.jira_client import post_comment
        post_comment(jira_id, jira_comment)
        logger.info("[reporter] Jira comment posted to %s", jira_id)
    except Exception as e:
        logger.error("[reporter] Failed to post Jira comment: %s", str(e))
        state["errors"].append({"agent": "reporter", "error": str(e)})

STEP 4 — Build email:
subject = f"QA Report: {jira_id} — {'All tests passed' if ui_fail==0 and api_fail==0 else f'{ui_fail+api_fail} test(s) failed'}"
email_body = f"Subject: {subject}\n\n{jira_comment}\n\nRun ID: {jira_id}\nTimestamp: {datetime.now().isoformat()}"

if USE_MOCK:
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
        with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT",587))) as s:
            s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD"))
            s.send_message(msg)
        logger.info("[reporter] Email sent to %s", os.getenv("EMAIL_RECIPIENTS"))
    except Exception as e:
        logger.error("[reporter] Failed to send email: %s", str(e))
        state["errors"].append({"agent": "reporter", "error": str(e)})

STEP 5 — ChromaDB (already done in Phase 3 — keep it, don't duplicate):
# Phase 3 ChromaDB write stays here — just verify it's still present

STEP 6 — Finalize:
state["status"] = "complete"
logger.info("[reporter] Run complete for %s — UI: %d pass %d healed %d fail | API: %d pass %d fail",
            jira_id, ui_pass, ui_healed, ui_fail, api_pass, api_fail)
return state

Also add to tools/jira_client.py:
def post_comment(jira_id: str, comment: str) -> None:
    """Post a comment on a Jira ticket."""
    if USE_MOCK:
        logger.info("[jira] MOCK: would post comment to %s", jira_id)
        return
    from atlassian import Jira
    client = Jira(url=os.getenv("JIRA_BASE_URL"),
                  username=os.getenv("JIRA_EMAIL"),
                  password=os.getenv("JIRA_API_TOKEN"))
    client.issue_add_comment(jira_id, comment)

## Task 3: graph/graph_builder.py — replace api stub with real api_node

Import api_node from agents/api_agent.
Replace the lambda stub with the real api_node.
No other changes to graph structure.

## Task 4: Update run.py — exit code logic

After graph.invoke(), add:
ui_results = final_state.get("ui_results") or {}
api_results = final_state.get("api_results") or {}

genuine_ui_failures = [
    r for r in ui_results.values()
    if r.get("status") == "fail"
]
genuine_api_failures = [
    r for r in api_results.values()
    if r.get("status") == "fail"
]

total_failures = len(genuine_ui_failures) + len(genuine_api_failures)
if total_failures > 0:
    logger.warning("Run completed with %d failure(s)", total_failures)
    sys.exit(1)
else:
    logger.info("Run completed — all tests passed or healed")
    sys.exit(0)

## Validation commands:

1. Full end-to-end run:
python run.py --jira PROJ-123

Must show ALL of these in output:
- "[orchestrator] Retrieved N past learnings from ChromaDB"
- "[analysis] Flows: [...]"
- "[test_script] ..."
- "[playwright] TC-001 → PASS / HEALED / FAIL"
- "[api_agent] Mock API results: N requests"
- "=== MOCK JIRA COMMENT ===" with formatted table
- "=== MOCK EMAIL ===" with subject line
- "=== ChromaDB: Learning written ==="
- "[reporter] Run complete for PROJ-123"

2. Exit code test:
python run.py --jira PROJ-123; echo "Exit code: $?"
# Must print: "Exit code: 0" when all pass/healed

3. Skip API test:
python -c "
import os; os.environ['USE_MOCK']='true'
from graph.state import create_initial_state
s = create_initial_state('PROJ-123')
s['skip_api'] = True
s['test_cases'] = [{'id':'TC-001','flow':'login','priority':'P1','given':'','when':'','then':'','type':'ui'}]
s['api_collection'] = {}
from agents.api_agent import api_node
result = api_node(s)
assert result['api_results'] == {}
assert result['status'] == 'api_skipped'
print('Skip API OK')
"

4. Reporter output check:
python run.py --jira PROJ-123 2>&1 | grep -E "(MOCK JIRA|MOCK EMAIL|ChromaDB)"
# Must show all 3 lines

## Phase 4 complete when:
- Full pipeline runs without exceptions
- Mock Jira comment appears with correct structure
- Mock email appears with correct subject
- ChromaDB write happens (already from Phase 3)
- Exit code 0 on all pass, 1 on genuine failures
- python run.py --jira PROJ-123 takes less than 60 seconds total
```

