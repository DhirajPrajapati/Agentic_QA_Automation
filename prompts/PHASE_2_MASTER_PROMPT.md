# Phase 2 Master Prompt
## Copy this entire prompt into Claude Chat

---

```
You are helping me build Phase 2 of the QA Orchestrator.
Phase 1 is complete and passing. Read CLAUDE.md before writing any code.

## PHASE 2 SCOPE:
Goal: Agent generates a Playwright script from the recording + test cases,
mock-runs it, displays pass/fail results per test case.

New files: test_script_agent.py, playwright_agent.py, reporter_agent.py (stub)
Updated files: graph_builder.py, graph/edges.py, run.py

## Task 1: agents/test_script_agent.py

test_script_node(state: QAState) -> QAState must:

PART A — UI Script Generation:
1. Extract user_type and module from state["jira_data"]["fields"]["labels"]
   - user_type: first of "investor", "distributor", "employee" found in labels
   - module: first of "login", "dashboard", "redemption", etc. found in labels
2. Call tools/recording_loader.load_recording(user_type, module)
3. If recording FOUND:
   - Build prompt:
     "You are a QA automation engineer. Given this Playwright recording of a
      happy path flow, add the following to it without changing existing selectors:
      1. expect() assertions after each navigation step
      2. Separate test functions for each negative test case in the test_cases list
         using the SAME selectors as the recording, different test data
      3. Add explicit page.wait_for_load_state() where needed
      Recording:\n{recording_content}
      Test cases:\n{json.dumps(test_cases)}
      Output: Complete Python Playwright file only. No explanation."
4. If recording NOT FOUND:
   - Extract selector hints from confluence_context (Section 8 — UI Element Hints)
   - Build prompt:
     "Generate a Playwright Python test file for these test cases.
      Use these UI element hints from the portal knowledge base:
      {selector_hints}
      Test cases: {json.dumps(test_cases)}
      WARNING: No recording available. Add comment at top of file:
      # WARNING: Generated without recording. Selectors may need manual verification."
5. Call llm_client.invoke_with_retry() with the prompt
6. Save script to outputs/scripts/{user_type}_{module}_{jira_id}.py
7. Write script content to state["ui_scripts"]
8. Log: recording found/not found, output file path

PART B — API Collection Enhancement:
1. Check if state["api_collection"] is None (Phase 1 test_script_agent didn't set it)
2. Call tools/collection_loader.load_collection(user_type, module)
3. If collection found:
   - Build prompt:
     "Given this Postman collection, add negative test cases for each request.
      For each existing request, add 2-3 negative variants:
      - Invalid/missing required fields
      - Wrong auth token
      - Boundary values
      Collection: {json.dumps(collection)}
      API test cases from test plan: {api_test_cases}
      Output: Complete valid Postman collection JSON only."
   - Parse LLM output as JSON safely
4. If no collection: set api_collection to minimal stub
5. Write to state["api_collection"]
6. Set state["status"] = "scripts_ready"
Return updated state.

## Task 2: agents/playwright_agent.py (MOCK EXECUTION)

playwright_node(state: QAState) -> QAState must:

1. Check USE_MOCK:

   MOCK MODE (USE_MOCK=true):
   - For each test case in state["test_cases"] where type == "ui":
     - Simulate execution result using weighted random:
       pass: 70%, healed: 20%, fail: 10%
     - Use random.choices(["pass","healed","fail"], weights=[70,20,10])
     - For "pass": duration_ms = random.randint(1200, 3500)
     - For "healed":
       duration_ms = random.randint(3000, 5500)
       mock original_selector = ".btn-" + tc["flow"].replace("_","-")
       mock healed_selector = f"button:has-text('{tc['flow'].replace('_',' ').title()}')"
       Call chromadb_client.write_healed_selector(original, healed, module, tc["flow"])
       Note: import chromadb_client only if it exists — graceful if not (Phase 3 adds it)
     - For "fail":
       error = f"Selector not found: .{tc['flow']}-container"
       screenshot_path = f"outputs/screenshots/{tc['id']}_fail.png"
   - Build ui_results dict:
     { "TC-001": {"status": "pass", "duration_ms": 2341}, ... }
   
   REAL MODE (USE_MOCK=false) — add placeholder:
   - Add TODO comment block explaining real Playwright execution
   - For now: log warning and return same mock results
   - "TODO Phase 5: Implement real browser execution here"

2. Write to state["ui_results"]
3. Log each test case result with status emoji
4. Log summary: X pass, Y healed, Z fail
5. Set state["status"] = "ui_complete"
Return updated state.

## Task 3: agents/reporter_agent.py (PHASE 2 STUB)

reporter_node(state: QAState) -> QAState must:
1. Build results summary string:
   "=== QA RUN RESULTS: {jira_id} ===\n"
   For each ui_result: print TC ID, flow name, status with emoji
   Summary line: "UI: X pass | Y healed | Z fail"
   If api_results is set: "API: X pass | Y fail"
2. Print the summary (this is the stub — real reporting in Phase 4)
3. Set state["status"] = "complete"
4. Log: "Run complete for {jira_id}"
5. Add TODO comments:
   "# TODO Phase 3: Write ChromaDB learning document"
   "# TODO Phase 4: Post real Jira comment"
   "# TODO Phase 4: Send email report"
Return updated state.

## Task 4: graph/edges.py — implement both functions

route_after_scripts(state: QAState) -> str:
  """Route after test_script_agent completes."""
  if state.get("skip_api", False):
      return "ui_only"
  return "both"
  # Note: both ui_only and "both" route to playwright first
  # api runs after playwright if skip_api is False

route_after_playwright(state: QAState) -> str:
  """Route after playwright_agent completes."""
  if state.get("skip_api", False):
      return "report"
  return "run_api"

## Task 5: graph/graph_builder.py — full Phase 2 graph

Import all nodes:
- orchestrator_node from agents/orchestrator_agent
- analysis_node from agents/analysis_agent
- test_case_node from agents/test_case_agent
- test_script_node from agents/test_script_agent
- playwright_node from agents/playwright_agent
- reporter_node from agents/reporter_agent

Build graph:
- All nodes from Phase 1 plus: test_script, playwright, reporter
- Entry: orchestrator
- Linear: orchestrator → analysis → test_case → test_script
- Conditional from test_script: route_after_scripts → {"ui_only":"playwright","both":"playwright"}
- Conditional from playwright: route_after_playwright → {"run_api":"api_stub","report":"reporter"}
- api_stub: add a lambda node that just returns state unchanged (api_agent comes in Phase 4)
- reporter → END

Note: Keep TODO comments for Phase 4 api node.

## Task 6: Update run.py for Phase 2

After graph invocation add:
- Print ui_results summary if present
- Print "Script saved to: outputs/scripts/..." if file exists
- Keep exit code 0 for Phase 2

## Validation commands — run all of these:

1. Basic agent test:
python -c "
import os; os.environ['USE_MOCK']='true'
from graph.state import create_initial_state
from agents.orchestrator_agent import orchestrator_node
from agents.analysis_agent import analysis_node
from agents.test_case_agent import test_case_node
from agents.test_script_agent import test_script_node
s = test_script_node(test_case_node(analysis_node(orchestrator_node(create_initial_state('PROJ-123')))))
assert s['ui_scripts'] is not None, 'ui_scripts is None'
assert 'def test_' in s['ui_scripts'], 'No test functions in script'
print('test_script_agent OK')
"

2. Full pipeline:
python run.py --jira PROJ-123

Expected output must include:
- "[test_script] Loaded recording: ..." OR "[test_script] No recording found"
- "[playwright] TC-001 ... → PASS" (or HEALED or FAIL)
- "=== QA RUN RESULTS: PROJ-123 ==="
- "UI: X pass | Y healed | Z fail"

3. Outputs check:
python -c "
import pathlib
scripts = list(pathlib.Path('outputs/scripts').glob('*.py'))
assert len(scripts) > 0, 'No script file generated'
print('Script generated:', scripts[0].name)
content = scripts[0].read_text()
assert 'def test_' in content
print('Script contains test functions OK')
"

4. Edge routing test (skip_api):
python -c "
from graph.state import create_initial_state
from graph.edges import route_after_scripts, route_after_playwright
s = create_initial_state('PROJ-123')
s['skip_api'] = True
assert route_after_scripts(s) == 'ui_only'
assert route_after_playwright(s) == 'report'
s['skip_api'] = False
assert route_after_scripts(s) == 'both'
assert route_after_playwright(s) == 'run_api'
print('Edge routing OK')
"

## Rules reminder:
- Recording content must reach LLM unmodified
- LLM must NOT invent selectors not present in the recording
- Mock execution uses weighted random — do not hardcode all as pass
- Gracefully handle missing chromadb_client import (Phase 3 adds it)
```

