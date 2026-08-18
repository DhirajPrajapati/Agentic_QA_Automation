# Phase 1 Master Prompt
## Copy this entire prompt into Claude Chat

---

```
You are helping me build Phase 1 of the QA Orchestrator — an Agentic QA
Automation System built in Python using LangGraph + LangChain + OpenAI.

Read the CLAUDE.md file in my project root before writing any code.
Follow every rule in it exactly. Do not skip any rule.

## PHASE 1 SCOPE — Build exactly this, nothing more:

Phase 1 goal: `python run.py --jira PROJ-123` reads mock data and prints
generated test cases to the terminal.

## Task list — complete in this exact order:

### Task 1: requirements.txt
Create requirements.txt with all packages from CLAUDE.md tech stack.
Add version comments. Group by purpose.

### Task 2: graph/state.py
Create QAState TypedDict exactly as in CLAUDE.md.
Add create_initial_state(jira_id: str) -> QAState factory.
Add inline comment on each field: which agent writes to it.

### Task 3: Mock data files
Create these files with realistic but fictional content:

mock_data/jira/PROJ-123.json
- Jira bug ticket: "Fix OTP not triggering for investor login on new device"
- Labels: ["investor", "login", "otp", "frontend"]
- Include: id, key, fields.summary, fields.description (3-paragraph BRD),
  fields.labels, fields.issuetype.name, fields.acceptance_criteria (3 items)

mock_data/confluence/investor_login.txt
- Simulates Confluence page for Investor Login module of a PMS portal
- Must include all 12 sections:
  1. Page Metadata (Jira labels: investor, login, otp)
  2. Module Overview
  3. User Roles (retail, institutional, NRI investor)
  4. URLs and Navigation (include UAT URLs)
  5. Happy Path Flows (standard login flow, OTP flow — step by step)
  6. Edge Cases (invalid password, locked account, expired OTP, invalid OTP)
     — include EXACT error message text for each
  7. API Endpoints (POST /login, POST /verify-otp, POST /forgot-password)
     — include request body, success response, all failure responses
  8. UI Element Hints (email input, password input, login button, OTP input,
     resend button — with CSS selectors, note button label changes)
  9. Test Data (UAT credentials for each user role, static OTP: 123456)
  10. Prerequisites (UAT must be up, test accounts must exist)
  11. Known Issues (OTP screen 4-5s load, login button label changes)
  12. Changelog (one sample entry)

mock_data/chromadb_seed/known_issues.json
- JSON array of 3 objects, each with: module, document, confidence
- Module: "investor/login"
- Issues: OTP slow load, button label change, OTP input layout varies

config/module_map.json
- Maps investor+login labels → "investor_login" (mock page ID)
- Maps investor+otp → "investor_login"  
- Maps investor+dashboard → "investor_dashboard"
- Maps distributor+login → "distributor_login"
- Maps employee+login → "employee_login"
Structure: { "investor": { "login": "investor_login", ... }, ... }

recordings/investor/login_happy_path.py
- Valid Python Playwright script
- Simulates VS Code recorder output for investor login on legacy portal
- URL: https://uat.example.com/investor/login
- Steps: goto, fill email, fill password, click Login button, wait_for_url dashboard
- Use text-based + CSS selectors (no data-testid)
- Add comment above each step explaining what it does
- Include a simple async test function

postman_collections/investor/login.postman_collection.json
- Valid Postman collection v2.1 format
- Include 2 requests:
  1. POST /api/v1/investor/login — body: email, password, device_id
  2. POST /api/v1/investor/verify-otp — body: otp, session_token
- Include test scripts (pm.test for status 200)
- Use {{base_url}} variable

### Task 4: Tool clients

tools/jira_client.py
- USE_MOCK pattern from CLAUDE.md
- get_ticket(jira_id: str) -> dict
- Mock: load from mock_data/jira/{jira_id}.json
- Real: use atlassian-python-api Jira class
- Full type hints, docstring, logging

tools/confluence_client.py
- USE_MOCK pattern
- get_page_by_id(page_id: str) -> str (plain text)
- resolve_page_ids(labels: list[str]) -> list[str]
  → reads config/module_map.json, returns matching page IDs
- Mock: resolve label combo → filename, load from mock_data/confluence/
- Real: GET /wiki/rest/api/content/{id}?expand=body.storage,
  parse HTML body with BeautifulSoup get_text()
- Full type hints, docstring, logging

tools/recording_loader.py
- load_recording(user_type: str, module: str) -> str | None
- Path pattern: recordings/{user_type}/{module}_happy_path.py
- Return None if file does not exist (no exception)
- Log whether recording was found or not

tools/collection_loader.py
- load_collection(user_type: str, module: str) -> dict | None
- Path: postman_collections/{user_type}/{module}.postman_collection.json
- Return None if not found

tools/llm_client.py
- IMPORTANT CONSTRAINT: the developer does not have an OpenAI key yet —
  it will be provided by the organization later. The module must work
  end-to-end with USE_MOCK=true and USE_MOCK_LLM=true and NO API key
  set at all.
- Add a USE_MOCK_LLM env var (default true, same pattern as USE_MOCK).
- On import:
  ```python
  api_key = os.getenv("OPENAI_API_KEY", "")
  if not api_key or api_key == "placeholder_add_org_key_later":
      logger.warning("[llm_client] No real OpenAI key set. LLM calls will fail.")
  ```
- Wrap ChatOpenAI(model=OPENAI_MODEL from .env)
- invoke_with_retry(messages: list, agent_type: str = "generic", max_attempts: int = 3) -> str
  - When USE_MOCK_LLM=true: return one hardcoded, realistic, valid-JSON
    mock response per agent_type ("analysis", "test_case",
    "test_script_ui", "test_script_api", "self_heal", falling back to
    "generic") — no network call, no API key required.
  - When USE_MOCK_LLM=false AND a real key is set: call ChatOpenAI for real.
  - Retry on RateLimitError, APIError with exponential backoff (1s, 2s, 4s)
- Log each attempt and retry

### Task 5: agents/orchestrator_agent.py

orchestrator_node(state: QAState) -> QAState must:
1. Call get_ticket(state["jira_id"]) — log ticket summary
2. Call resolve_page_ids(jira_data["fields"]["labels"]) → page IDs
3. For each page ID: call get_page_by_id() → join all results with "\n\n"
4. Write jira_data, confluence_context to state
5. Set past_failures = [] (Phase 3 will add ChromaDB here)
6. Set status = "orchestrator_complete"
7. Log: ticket fetched, confluence pages fetched, character count
8. Wrap all calls in try/except → log to state["errors"]
Return updated state.

### Task 6: agents/analysis_agent.py

analysis_node(state: QAState) -> QAState must:
1. Build LLM prompt including:
   - Jira summary and acceptance criteria
   - Confluence context (first 3000 chars)
   - Past failures (empty list in Phase 1)
   - Instruction: "Output ONLY valid JSON, no markdown, no explanation"
2. JSON output schema:
   {
     "flows_to_test": ["flow_name_1", "flow_name_2"],
     "skip_api": false,
     "risk_areas": ["description of flaky area 1"],
     "user_types_in_scope": ["retail_investor"]
   }
3. Parse JSON safely — on JSONDecodeError: log error, set minimal defaults
4. Determine skip_api: true if labels contain only frontend terms
5. Write all 4 fields to state
6. Set status = "analysis_complete"
7. Log: flows to test, skip_api value, number of risk areas
Return updated state.

### Task 7: agents/test_case_agent.py

test_case_node(state: QAState) -> QAState must:
1. For each flow in state["flows_to_test"]:
   Build prompt including flow name, Confluence Section 6 edge cases,
   acceptance criteria, risk areas
   "Output ONLY a valid JSON array of test case objects. No markdown."
2. Each test case object schema:
   {
     "id": "TC-001",
     "flow": "standard_login",
     "priority": "P1",
     "given": "User is on /investor/login",
     "when": "User enters valid email and password and clicks Login",
     "then": "User is redirected to /investor/dashboard",
     "type": "ui"
   }
3. Minimum per flow: 1 P1 happy path + 1 P2 negative case
4. API test cases have type: "api"
5. Parse JSON safely — handle malformed LLM output
6. Collect all cases across all flows into one list
7. Write to state["test_cases"]
8. Set status = "test_cases_complete"
9. Log: total generated, breakdown by priority
Return updated state.

### Task 8: graph/graph_builder.py (Phase 1 — linear only)

Build StateGraph(QAState) with:
- Nodes: orchestrator, analysis, test_case
- Entry: orchestrator
- Edges: orchestrator → analysis → test_case → END
- Add comment: "# TODO Phase 2: Add test_script, playwright, api, reporter nodes"
- Add comment: "# TODO Phase 2: Add conditional edges"
Compile and return graph.

### Task 9: graph/edges.py

Stub file with:
- route_after_scripts(state: QAState) -> str: raises NotImplementedError + TODO
- route_after_playwright(state: QAState) -> str: raises NotImplementedError + TODO
With docstrings explaining what each will do in Phase 2.

### Task 10: run.py

Exactly as in CLAUDE.md run.py section.
After graph.invoke():
- Pretty-print state["test_cases"] as formatted JSON (json.dumps indent=2)
- Print summary line: "Generated {N} test cases for {jira_id}"
- Exit code 0 always in Phase 1

### Task 11: .env.example

Exactly as in CLAUDE.md .env.example section.

### Task 12: README.md

Short README with:
- What this project is (2 sentences)
- Setup: pip install, playwright install, create .env, python run.py
- Current phase: Phase 1
- Note: USE_MOCK=true for local development

## Validation — run this at the end and confirm it passes:
python run.py --jira PROJ-123

Expected:
- No exceptions
- Log lines from all 3 agents visible
- Test cases printed as formatted JSON
- At least 4 test cases generated
- At least 1 P1 and 1 P2 test case present

## Rules reminder from CLAUDE.md:
- No print() for logging — use logger
- No hardcoded credentials anywhere
- Full type hints on every function
- Docstrings on every public function
- Mock/real pattern on every external client
- No agent imports another agent
```

