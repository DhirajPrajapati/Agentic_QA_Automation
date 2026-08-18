# QA Orchestrator — Phase-Wise Implementation Plan
## Checklists + Validation Commands + Copilot Prompts

---

## Golden Rules Before You Start

1. Work one phase at a time. Never start Phase N+1 until Phase N validation passes.
2. Run the validation command at the end of every phase — not before.
3. Every Copilot prompt in this plan starts with `[PHASE-N]` so Copilot stays scoped.
4. When moving to office laptop: only `.env` values and files in `recordings/`,
   `postman_collections/`, and `config/module_map.json` change. Zero code changes.

---

## About the Zip File

**Do NOT put the documentation .md files into your agents/ or graph/ folders.**
They are reference material — not code.

**Do this instead:**
```
qa-orchestrator/
├── docs/              ← Put all .md files here
│   ├── 01_overview.md
│   ├── 02_architecture.md
│   └── ...
├── CLAUDE.md          ← Only this goes in root
├── agents/
└── ...
```

Copilot reads CLAUDE.md from the root. It should NOT read the docs/ files
as instructions. The docs are for you and your team to reference.

---

## Phase 1 — Core Loop
**Goal:** `python run.py --jira PROJ-123` reads mock data, prints test cases.
**Builds:** Scaffold, mock data, Jira/Confluence clients, orchestrator, analysis, test_case agents.
**Does NOT build:** Playwright, API testing, ChromaDB, reporting.

---

### 1.1 Project Scaffold

- [ ] Create root folder `qa-orchestrator/`
- [ ] Create all subfolders from CLAUDE.md folder structure
- [ ] Create `requirements.txt`
- [ ] Create `.env.example` (from CLAUDE.md)
- [ ] Copy `.env.example` to `.env` — add your real OpenAI key
- [ ] Create `.gitignore`:
  ```
  .env
  memory/
  outputs/
  __pycache__/
  *.pyc
  .pytest_cache/
  ```
- [ ] Create empty `__init__.py` in `agents/`, `graph/`, `tools/`
- [ ] Run: `pip install -r requirements.txt`

**Validation:**
```bash
python -c "import langgraph, langchain, chromadb; print('Imports OK')"
```

---

### 1.2 QAState

- [ ] Create `graph/state.py` with full TypedDict from CLAUDE.md
- [ ] Add `create_initial_state(jira_id: str) -> QAState` factory function
- [ ] Every field has an inline comment naming which agent writes to it

**Validation:**
```python
from graph.state import create_initial_state
s = create_initial_state("PROJ-123")
assert s["jira_id"] == "PROJ-123"
assert s["status"] == "initialising"
print("State OK")
```

---

### 1.3 Mock Data Files

- [ ] `mock_data/jira/PROJ-123.json` — investor OTP bug, labels: investor, login, otp
- [ ] `mock_data/confluence/investor_login.txt` — all 12 sections, realistic content
- [ ] `mock_data/chromadb_seed/known_issues.json` — 3+ known issues for investor/login
- [ ] `recordings/investor/login_happy_path.py` — valid Playwright Python, 5+ steps
- [ ] `postman_collections/investor/login.postman_collection.json` — valid v2.1 format
- [ ] `config/module_map.json` — maps `investor+login` → `investor_login`

**Validation:**
```bash
python -c "
import json, pathlib
j = json.load(open('mock_data/jira/PROJ-123.json'))
assert 'investor' in j['fields']['labels'], 'Missing label'
assert pathlib.Path('mock_data/confluence/investor_login.txt').exists()
assert pathlib.Path('recordings/investor/login_happy_path.py').exists()
print('Mock data OK')
"
```

---

### 1.4 Tool Clients

- [ ] `tools/jira_client.py` — `get_ticket(jira_id) -> dict`
- [ ] `tools/confluence_client.py`
  - `get_page_by_id(page_id) -> str`
  - `resolve_page_ids(labels: list[str]) -> list[str]`
- [ ] `tools/recording_loader.py` — `load_recording(user_type, module) -> str | None`
- [ ] `tools/collection_loader.py` — `load_collection(user_type, module) -> dict | None`
- [ ] `tools/llm_client.py` — OpenAI wrapper with 3-attempt retry

**Validation:**
```bash
python -c "
import os; os.environ['USE_MOCK']='true'
from tools.jira_client import get_ticket
from tools.confluence_client import resolve_page_ids
t = get_ticket('PROJ-123')
assert t['id'] == 'PROJ-123'
ids = resolve_page_ids(['investor','login'])
assert len(ids) > 0
print('Clients OK')
"
```

---

### 1.5 Orchestrator Agent

- [ ] `agents/orchestrator_agent.py`
  - `orchestrator_node(state: QAState) -> QAState`
  - Calls `get_ticket()`, `resolve_page_ids()`, `get_page_by_id()`
  - Writes `jira_data`, `confluence_context` to state
  - Sets `past_failures = []` (Phase 3 adds ChromaDB)
  - Logs every step

**Validation:**
```bash
python -c "
import os; os.environ['USE_MOCK']='true'
from graph.state import create_initial_state
from agents.orchestrator_agent import orchestrator_node
s = orchestrator_node(create_initial_state('PROJ-123'))
assert s['jira_data']['id'] == 'PROJ-123'
assert len(s['confluence_context']) > 100
print('Orchestrator OK')
"
```

---

### 1.6 Analysis Agent

- [ ] `agents/analysis_agent.py`
  - `analysis_node(state: QAState) -> QAState`
  - LLM reads `jira_data` + `confluence_context`
  - LLM outputs JSON: `flows_to_test`, `skip_api`, `risk_areas`, `user_types_in_scope`
  - Parse safely — handle malformed JSON
  - Writes all 4 fields to state

**Validation:**
```bash
python -c "
import os; os.environ['USE_MOCK']='true'
# Run through orchestrator first, then analysis
from graph.state import create_initial_state
from agents.orchestrator_agent import orchestrator_node
from agents.analysis_agent import analysis_node
s = analysis_node(orchestrator_node(create_initial_state('PROJ-123')))
assert len(s['flows_to_test']) > 0
assert isinstance(s['skip_api'], bool)
print('Analysis OK — flows:', s['flows_to_test'])
"
```

---

### 1.7 Test Case Agent

- [ ] `agents/test_case_agent.py`
  - `test_case_node(state: QAState) -> QAState`
  - LLM generates per-flow test cases as JSON array
  - Each item: `id`, `flow`, `priority`, `given`, `when`, `then`, `type`
  - Minimum: 1 P1 happy path + 1 P2 negative case per flow
  - Writes `test_cases` to state

**Validation:**
```bash
python -c "
import os; os.environ['USE_MOCK']='true'
from graph.state import create_initial_state
from agents.orchestrator_agent import orchestrator_node
from agents.analysis_agent import analysis_node
from agents.test_case_agent import test_case_node
s = test_case_node(analysis_node(orchestrator_node(create_initial_state('PROJ-123'))))
assert len(s['test_cases']) >= 4
assert any(tc['priority'] == 'P1' for tc in s['test_cases'])
print(f'Test cases OK — {len(s[\"test_cases\"])} generated')
"
```

---

### 1.8 Graph Builder + run.py

- [ ] `graph/graph_builder.py` — Phase 1: linear graph, no conditional edges
  - Nodes: orchestrator → analysis → test_case → END
  - Note comment: "Conditional edges added in Phase 2"
- [ ] `graph/edges.py` — stub file with TODO comments only
- [ ] `run.py` — accepts `--jira`, loads .env, invokes graph, prints test_cases

**Phase 1 Final Validation:**
```bash
python run.py --jira PROJ-123
```
Expected output:
```
[orchestrator] Fetching Jira: PROJ-123
[analysis] Flows: ['standard_login', 'otp_trigger', 'otp_verify']
[test_case] Generated 6 test cases (P1:3, P2:2, P3:1)

Generated 6 test cases for PROJ-123:
[{"id": "TC-001", "flow": "standard_login", ...}, ...]
```

**Phase 1 complete when:**
- [ ] `python run.py --jira PROJ-123` runs without exceptions
- [ ] Console shows formatted test case JSON
- [ ] All 3 agent log messages appear in order
- [ ] No credentials hardcoded anywhere

---

## Phase 2 — UI Script Generation + Mock Execution
**Goal:** Agent generates Playwright script, mock-runs it, shows pass/fail results.
**Builds:** `test_script_agent`, `playwright_agent` (mock), reporter stub, conditional edges.

---

### 2.1 Test Script Agent

- [ ] `agents/test_script_agent.py`
  - `test_script_node(state: QAState) -> QAState`
  - Loads recording via `recording_loader.load_recording()`
  - If found: LLM adds assertions + negative variants on top of recording
  - If not found: LLM generates from Confluence Section 8 hints (adds warning comment)
  - Saves to `outputs/scripts/{user_type}_{module}_{jira_id}.py`
  - Writes script string to `state["ui_scripts"]`

- [ ] `agents/test_script_agent.py` also handles API collection:
  - Loads Postman collection via `collection_loader.load_collection()`
  - LLM adds negative test cases
  - Writes to `state["api_collection"]`

**Validation:**
```bash
python -c "
import os; os.environ['USE_MOCK']='true'
# Chain through Phase 1 agents first
from graph.state import create_initial_state
from agents.orchestrator_agent import orchestrator_node
from agents.analysis_agent import analysis_node
from agents.test_case_agent import test_case_node
from agents.test_script_agent import test_script_node
import pathlib
s0 = create_initial_state('PROJ-123')
s1 = test_script_node(test_case_node(analysis_node(orchestrator_node(s0))))
assert s1['ui_scripts'] is not None
assert 'def test_' in s1['ui_scripts']
files = list(pathlib.Path('outputs/scripts').glob('*.py'))
assert len(files) > 0
print('Script agent OK — generated:', files[0].name)
"
```

---

### 2.2 Playwright Agent (Mock Mode)

- [ ] `agents/playwright_agent.py`
  - `playwright_node(state: QAState) -> QAState`
  - USE_MOCK=true: simulate each UI test case (70% pass, 20% healed, 10% fail)
  - For "healed": generate mock healed selector string
  - For "fail": generate mock error + screenshot path
  - Writes `ui_results` dict to state
  - TODO comment: "Real browser execution added in Phase 5"

**Validation:**
```bash
python -c "
import os; os.environ['USE_MOCK']='true'
# Full chain
from graph.state import create_initial_state
from agents.orchestrator_agent import orchestrator_node
from agents.analysis_agent import analysis_node
from agents.test_case_agent import test_case_node
from agents.test_script_agent import test_script_node
from agents.playwright_agent import playwright_node
s = playwright_node(test_script_node(test_case_node(analysis_node(orchestrator_node(create_initial_state('PROJ-123'))))))
assert s['ui_results'] is not None
statuses = [v['status'] for v in s['ui_results'].values()]
assert all(st in ['pass','fail','healed'] for st in statuses)
print('Playwright agent OK — results:', statuses)
"
```

---

### 2.3 Reporter Stub + Graph Update

- [ ] `agents/reporter_agent.py` — Phase 2 stub
  - `reporter_node(state: QAState) -> QAState`
  - Print formatted results summary to console only
  - No Jira posting, no email, no ChromaDB yet (Phase 3 + 4)
  - Sets `state["status"] = "complete"`

- [ ] Update `graph/edges.py`:
  - `route_after_scripts(state) -> str` — returns "ui_only" or "both"
  - `route_after_playwright(state) -> str` — returns "run_api" or "report"

- [ ] Update `graph/graph_builder.py`:
  - Add test_script, playwright, reporter nodes
  - Add conditional edges from CLAUDE.md graph structure
  - api node → stub (Phase 4)

**Phase 2 Final Validation:**
```bash
python run.py --jira PROJ-123
```
Expected new output (after Phase 1 output):
```
[test_script] Loaded recording: recordings/investor/login_happy_path.py
[test_script] Generated script: outputs/scripts/investor_login_PROJ-123.py
[playwright] TC-001 standard_login → PASS (2341ms)
[playwright] TC-002 otp_trigger → HEALED (selector fixed)
[playwright] TC-003 otp_verify → PASS (1823ms)
--- Results: 5 pass, 1 healed, 0 fail ---
```

**Phase 2 complete when:**
- [ ] Script file appears in `outputs/scripts/`
- [ ] All test cases show a status (pass/healed/fail)
- [ ] Graph runs end-to-end without exception
- [ ] Conditional edges route correctly (check with skip_api=True manually)

---

## Phase 3 — Self-Learning + ChromaDB
**Goal:** Every run writes to ChromaDB. Next run reads past learnings. Healing writes to memory.

---

### 3.1 ChromaDB Client

- [ ] `tools/chromadb_client.py`
  - `query_past_failures(module, summary, n=5) -> list[str]`
  - `write_learning(doc: str, metadata: dict) -> None`
  - `write_healed_selector(original, healed, module, element) -> None`
  - Uses `chromadb.PersistentClient(path=CHROMADB_PATH)`
  - Collection name: `"qa_learnings"`

**Validation:**
```bash
python -c "
from tools.chromadb_client import write_learning, query_past_failures
write_learning('OTP screen is slow on UAT', {'module':'investor/login','jira_id':'TEST'})
results = query_past_failures('investor/login', 'OTP slow')
assert len(results) >= 1
print('ChromaDB client OK — stored and retrieved')
"
```

---

### 3.2 Seed Script

- [ ] `scripts/seed_chromadb.py`
  - Loads `mock_data/chromadb_seed/known_issues.json`
  - Calls `write_learning()` for each issue
  - Prints confirmation count

**Run and validate:**
```bash
python scripts/seed_chromadb.py
# Output: "Seeded 3 documents to ChromaDB"
python -c "
from tools.chromadb_client import query_past_failures
r = query_past_failures('investor/login', 'OTP not triggering')
print(f'Seed check: {len(r)} results found')
assert len(r) >= 1
"
```

---

### 3.3 Update Orchestrator — Add ChromaDB Query

- [ ] Update `agents/orchestrator_agent.py`
  - After fetching Confluence: call `chromadb_client.query_past_failures()`
  - Write results to `state["past_failures"]`
  - Log: how many past learnings retrieved

**Validation:**
```bash
# Seed first if not done
python scripts/seed_chromadb.py
python -c "
import os; os.environ['USE_MOCK']='true'
from graph.state import create_initial_state
from agents.orchestrator_agent import orchestrator_node
s = orchestrator_node(create_initial_state('PROJ-123'))
print(f'Past failures retrieved: {len(s[\"past_failures\"])}')
assert len(s['past_failures']) >= 1
"
```

---

### 3.4 Update Playwright Agent — Write Healed Selectors

- [ ] Update `agents/playwright_agent.py`
  - On "healed" result: call `chromadb_client.write_healed_selector()`
  - Log: healed selector written to ChromaDB

---

### 3.5 Update Reporter — Write Reflection Doc

- [ ] Update `agents/reporter_agent.py`
  - After printing results: call `chromadb_client.write_learning()` with:
    - failures list
    - healed selectors
    - timing observations
    - jira_id in metadata

**Phase 3 Final Validation:**
```bash
python run.py --jira PROJ-123
# Run it TWICE
python run.py --jira PROJ-123

# Second run must show:
# [orchestrator] Retrieved N past learnings from ChromaDB
```

**Phase 3 complete when:**
- [ ] First run: ChromaDB has seeded docs only
- [ ] Second run: log shows past learnings retrieved from first run
- [ ] Self-healing writes to ChromaDB visible in second run
- [ ] `memory/chromadb/` folder exists and has data

---

## Phase 4 — API Testing + Full Reporting
**Goal:** Newman runs. Mock Jira comment + email print to console. Full pipeline end-to-end.

---

### 4.1 API Agent

- [ ] `agents/api_agent.py`
  - `api_node(state: QAState) -> QAState`
  - If `skip_api=True`: set `api_results={}`, return immediately
  - USE_MOCK=true: return mock Newman results (2-3 passing requests)
  - USE_MOCK=false: run Newman via subprocess, parse JSON report
  - Writes `api_results` to state

**Validation:**
```bash
python -c "
import os; os.environ['USE_MOCK']='true'
from graph.state import create_initial_state
s = create_initial_state('PROJ-123')
s['api_collection'] = {'name':'test','requests':[]}
s['skip_api'] = False
from agents.api_agent import api_node
result = api_node(s)
assert result['api_results'] is not None
print('API agent OK — results:', result['api_results'])
"
```

---

### 4.2 Reporter Agent — Full Version

- [ ] Update `agents/reporter_agent.py` — full implementation
  - Build structured Jira comment string (pass/fail table, healed list, errors)
  - USE_MOCK=true: print with `"=== MOCK JIRA COMMENT ==="` prefix
  - USE_MOCK=false: call `jira_client` to post real comment
  - USE_MOCK=true: print email with `"=== MOCK EMAIL ==="` prefix
  - USE_MOCK=false: send via SMTP
  - Always: write ChromaDB reflection doc (already in Phase 3)

---

### 4.3 Update Graph + run.py Exit Code

- [ ] Update `graph/graph_builder.py` — add api node (was stub before)
- [ ] Update `run.py` — add exit code logic:
  ```python
  failures = [r for r in final_state['ui_results'].values()
              if r['status'] == 'fail']
  sys.exit(1 if failures else 0)
  ```

**Phase 4 Final Validation:**
```bash
python run.py --jira PROJ-123
```
Must show in console:
```
=== MOCK JIRA COMMENT ===
QA Report — PROJ-123
UI: 5 pass | 1 healed | 0 fail
API: 3 pass | 0 fail
[TC-001] standard_login ✅ PASS
[TC-002] otp_trigger ⚡ HEALED
...
=== MOCK EMAIL ===
Subject: QA Report: PROJ-123 — All tests passed
...
=== ChromaDB: Learning written ===
```

**Phase 4 complete when:**
- [ ] Full run shows all 4 sections: results, mock Jira, mock email, ChromaDB write
- [ ] `python run.py --jira PROJ-123; echo "Exit: $?"` shows `Exit: 0` on all pass
- [ ] Pipeline handles `--skip-api` flag correctly

---

## Phase 5 — GitHub Actions (Office Laptop Only)
**Goal:** PR merge → auto-trigger → real Jira comment.

---

### 5.1 Prep Office Laptop

- [ ] Clone repo from GitHub: `git clone ...`
- [ ] `pip install -r requirements.txt`
- [ ] `playwright install chromium`
- [ ] `npm install -g newman`
- [ ] Copy `.env.example` to `.env` — fill ALL real values
- [ ] Set `USE_MOCK=false` in `.env`

### 5.2 Swap Real Data

- [ ] Update `config/module_map.json` with real Confluence page IDs
- [ ] Record happy paths using VS Code Playwright extension → `recordings/`
- [ ] Get Postman collections from BE team → `postman_collections/`
- [ ] Run `python scripts/seed_chromadb.py`

### 5.3 Test Manual Run

- [ ] `python run.py --jira REAL-TICKET-ID`
- [ ] Verify real Jira comment appears on the ticket
- [ ] Fix any API/credential issues

### 5.4 GitHub Actions

- [ ] Install self-hosted runner on office laptop
- [ ] Create `.github/workflows/qa-trigger.yml`
- [ ] Merge a test PR to UAT branch
- [ ] Verify Actions fires → verify Jira comment posted

**Phase 5 complete when:**
- [ ] PR merge triggers run automatically with no manual steps
- [ ] Jira ticket gets a real structured comment within 8 minutes

---

## Phase 6 — Server Deployment (Optional)
**Goal:** 24/7 operation. Office laptop not required.

- [ ] Create `Dockerfile` for Python app
- [ ] Create `docker-compose.yml` — app + ChromaDB server containers
- [ ] Move self-hosted runner to server
- [ ] Secure env vars on server (not `.env` file)
- [ ] Run 5 consecutive automated runs without manual intervention
- [ ] Verify ChromaDB persists between restarts

---

## Office Laptop Migration — Exact Commands

```bash
# On personal laptop — push final Phase 4 code
git add . && git commit -m "feat: Phase 4 complete" && git push

# On office laptop
git clone https://github.com/your-org/qa-orchestrator.git
cd qa-orchestrator
pip install -r requirements.txt
playwright install chromium
npm install -g newman
cp .env.example .env
# Edit .env: USE_MOCK=false + all real tokens

# Swap data
# 1. Edit config/module_map.json with real Confluence page IDs
# 2. Record flows → recordings/investor/login_happy_path.py
# 3. Get BE collections → postman_collections/investor/login.json

# Seed and test
python scripts/seed_chromadb.py
python run.py --jira REAL-PROJ-123

# Verify Jira comment appeared — then proceed to Phase 5
```

**Zero code changes. Config + files only.**

