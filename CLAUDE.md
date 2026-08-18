# QA Orchestrator — CLAUDE.md
## Master instruction file for Claude

> This file is read automatically by claude when the project
> is open in VS Code. Every code suggestion Copilot makes must follow
> these rules. Do not delete or rename this file.

---

## What This Project Is

An **Agentic QA Automation System** — a Python multi-agent pipeline
built on LangGraph that:

1. Reads a Jira ticket (mock locally / real on office laptop)
2. Fetches Confluence module knowledge (mock locally / real on office laptop)
3. Queries ChromaDB for past test learnings (always real — local)
4. Generates test cases via LLM
5. Generates Playwright UI scripts + Postman API collections
6. Executes tests, self-heals broken selectors
7. Reports results to Jira + email, writes learnings to ChromaDB

**Environment rule:** Everything external is MOCKED locally using
JSON/text files. The swap to real is a `.env` value change + file
drop — zero code changes.

---

## Non-Negotiable Rules

1. **Never invent selectors.** Playwright scripts always load a
   recording file first. LLM only adds assertions on top.
2. **Never hardcode credentials.** All secrets live in `.env` only.
3. **Never share state between agents directly.** All data flows
   through `QAState` only.
4. **Every external client checks `USE_MOCK` env var** and falls back
   to local files when true.
5. **No agent imports another agent.** Agents only import from
   `tools/` and `graph/`.
6. **Full type hints on every function.** No exceptions.
7. **Docstrings on every class and public function.**
8. **Use `python-dotenv` to load env.** Never `os.environ` directly.
9. **Log with `logging` module.** Never `print()` for runtime output.
10. **Wrap every external call in try/except.** Log errors to
    `state["errors"]`. Never let one failure crash the whole run.

---

## Tech Stack — Use Only These Libraries

| Purpose            | Library                          | Min version |
|--------------------|----------------------------------|-------------|
| Orchestration      | `langgraph`                      | 0.2.0       |
| LLM framework      | `langchain`, `langchain-openai`  | 0.3.0       |
| LLM provider       | OpenAI `gpt-4o`                  | via API     |
| UI testing         | `playwright`                     | 1.45.0      |
| API testing        | Newman CLI                       | subprocess  |
| Vector memory      | `chromadb`                       | 0.5.0       |
| Jira + Confluence  | `atlassian-python-api`           | 3.41.0      |
| HTML parsing       | `beautifulsoup4`                 | 4.12.0      |
| Config             | `python-dotenv`                  | 1.0.0       |
| Validation         | `pydantic`                       | 2.0.0       |

Do not add any other library without explicit instruction.

---

## Folder Structure — Never Deviate

```
qa-orchestrator/
├── agents/
│   ├── __init__.py
│   ├── orchestrator_agent.py
│   ├── analysis_agent.py
│   ├── test_case_agent.py
│   ├── test_script_agent.py
│   ├── playwright_agent.py
│   ├── api_agent.py
│   └── reporter_agent.py
├── graph/
│   ├── __init__.py
│   ├── state.py
│   ├── graph_builder.py
│   └── edges.py
├── tools/
│   ├── __init__.py
│   ├── jira_client.py
│   ├── confluence_client.py
│   ├── chromadb_client.py
│   ├── recording_loader.py
│   ├── collection_loader.py
│   └── llm_client.py
├── recordings/
│   ├── investor/login_happy_path.py
│   ├── distributor/login_happy_path.py
│   └── employee/login_happy_path.py
├── postman_collections/
│   ├── investor/login.postman_collection.json
│   ├── distributor/login.postman_collection.json
│   └── employee/login.postman_collection.json
├── mock_data/
│   ├── jira/PROJ-123.json
│   ├── confluence/investor_login.txt
│   └── chromadb_seed/known_issues.json
├── config/
│   ├── module_map.json
│   └── postman_environments/uat_investor.postman_environment.json
├── memory/chromadb/          ← gitignored, auto-created
├── outputs/
│   ├── scripts/
│   ├── collections/
│   ├── reports/
│   └── screenshots/
├── scripts/seed_chromadb.py
├── tests/
│   ├── test_analysis_agent.py
│   ├── test_test_case_agent.py
│   └── test_reporter_agent.py
├── .github/workflows/qa-trigger.yml
├── run.py
├── .env                      ← gitignored
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## QAState — Single Source of Truth

```python
# graph/state.py — exact definition, never add fields without
# updating this file first

from typing import TypedDict, Optional

class QAState(TypedDict):
    # Inputs — written by orchestrator_agent
    jira_id:              str
    jira_data:            dict
    confluence_context:   str
    past_failures:        list

    # Analysis — written by analysis_agent
    flows_to_test:        list
    skip_api:             bool
    risk_areas:           list
    user_types_in_scope:  list

    # Generation — written by test_case_agent + test_script_agent
    test_cases:           list
    ui_scripts:           Optional[str]
    api_collection:       Optional[dict]

    # Execution — written by playwright_agent + api_agent
    ui_results:           Optional[dict]
    api_results:          Optional[dict]

    # Control — managed by orchestrator + each agent
    status:               str
    retry_count:          int
    errors:               list
    current_phase:        str
```

---

## Mock/Real Pattern — Apply to Every External Client

```python
# Pattern every client must follow:

import os, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"

def get_ticket(jira_id: str) -> dict:
    """Fetch Jira ticket. Mock if USE_MOCK=true."""
    if USE_MOCK:
        path = Path(f"mock_data/jira/{jira_id}.json")
        return json.loads(path.read_text())
    from atlassian import Jira
    client = Jira(
        url=os.getenv("JIRA_BASE_URL"),
        username=os.getenv("JIRA_EMAIL"),
        password=os.getenv("JIRA_API_TOKEN")
    )
    return client.issue(jira_id)
```

Apply `USE_MOCK` to: `jira_client`, `confluence_client`,
`reporter_agent` (Jira posting + email), `playwright_agent`
(browser execution).

ChromaDB is always real — it works locally, no credentials needed.

---

## Agent Responsibilities (One Job Each)

| Agent | Reads from state | Writes to state |
|---|---|---|
| `orchestrator_agent` | `jira_id` | `jira_data`, `confluence_context`, `past_failures` |
| `analysis_agent` | `jira_data`, `confluence_context`, `past_failures` | `flows_to_test`, `skip_api`, `risk_areas`, `user_types_in_scope` |
| `test_case_agent` | `jira_data`, `confluence_context`, `flows_to_test` | `test_cases` |
| `test_script_agent` | `test_cases`, `confluence_context` | `ui_scripts`, `api_collection` |
| `playwright_agent` | `ui_scripts`, `past_failures` | `ui_results` |
| `api_agent` | `api_collection`, `skip_api` | `api_results` |
| `reporter_agent` | all results | writes to ChromaDB, Jira, email |

---

## LangGraph Graph Structure

```python
# graph/graph_builder.py — full structure

from langgraph.graph import StateGraph, END
from graph.state import QAState

def build_graph():
    g = StateGraph(QAState)
    g.add_node("orchestrator",  orchestrator_node)
    g.add_node("analysis",      analysis_node)
    g.add_node("test_case",     test_case_node)
    g.add_node("test_script",   test_script_node)
    g.add_node("playwright",    playwright_node)
    g.add_node("api",           api_node)
    g.add_node("reporter",      reporter_node)

    g.set_entry_point("orchestrator")
    g.add_edge("orchestrator", "analysis")
    g.add_edge("analysis",     "test_case")
    g.add_edge("test_case",    "test_script")

    g.add_conditional_edges("test_script", route_after_scripts, {
        "ui_only": "playwright",
        "both":    "playwright",
    })
    g.add_conditional_edges("playwright", route_after_playwright, {
        "run_api": "api",
        "report":  "reporter",
    })
    g.add_edge("api",      "reporter")
    g.add_edge("reporter", END)
    return g.compile()
```

---

## Self-Healing Pattern (inside playwright_agent)

```python
MAX_HEAL_ATTEMPTS = 3

def self_heal(failed_selector, test_intent, screenshot_path,
              confluence_hints, past_heals, llm) -> tuple[str|None, bool]:
    """Suggest alternative selectors. Returns (working, success)."""
    alternatives = llm.suggest_selectors(
        failed_selector=failed_selector,
        test_intent=test_intent,
        screenshot_path=screenshot_path,
        hints=confluence_hints,
        past_heals=past_heals,
        n=MAX_HEAL_ATTEMPTS
    )
    for selector in alternatives:
        if try_selector(selector):
            return selector, True
    return None, False
```

---

## Coding Standards

### File header (every file)
```python
"""
{module} — {one-line description}
Part of: QA Orchestrator
Phase: {1|2|3|4|5|6}
Mock-safe: {yes|no}
"""
```

### Logging pattern
```python
import logging
logger = logging.getLogger(__name__)
logger.info("[orchestrator] Fetching ticket: %s", jira_id)
logger.warning("[playwright] Self-healing: %s", failed_selector)
logger.error("[api_agent] Newman failed: %s", err)
```

### Error handling pattern
```python
try:
    result = external_call()
except Exception as e:
    logger.error("[agent] Call failed: %s", str(e))
    state["errors"].append({"agent": "name", "error": str(e)})
    # Do not raise — let reporter handle failures
```

### LLM prompt pattern
```python
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

llm = ChatOpenAI(model="gpt-4o")
prompt = ChatPromptTemplate.from_template(template)
chain = prompt | llm
result = chain.invoke(kwargs)
```

---

## .env.example

```env
# === MOCK MODE ===
# true = use local files (personal laptop)
# false = use real APIs (office laptop)
USE_MOCK=true

# === OPENAI — required always ===
OPENAI_API_KEY=your_openai_key_here
OPENAI_MODEL=gpt-4o

# === JIRA — only needed when USE_MOCK=false ===
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.email@company.com
JIRA_API_TOKEN=your_jira_token

# === CONFLUENCE — only needed when USE_MOCK=false ===
CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net
CONFLUENCE_EMAIL=your.email@company.com
CONFLUENCE_API_TOKEN=your_confluence_token

# === UAT — only needed when USE_MOCK=false ===
UAT_BASE_URL=https://uat.yourportal.com

# === CHROMADB — always local ===
CHROMADB_PATH=./memory/chromadb

# === EMAIL — only needed when USE_MOCK=false ===
SMTP_HOST=smtp.yourcompany.com
SMTP_PORT=587
SMTP_USER=qa-reports@yourcompany.com
SMTP_PASSWORD=your_smtp_password
EMAIL_RECIPIENTS=qa@yourcompany.com
```

---

## Phase Prefixing Rule for Copilot Prompts

Always start every Copilot Chat prompt with the current phase tag:

```
[PHASE-1] Write the orchestrator_agent.py ...
[PHASE-2] Add Playwright mock execution to playwright_agent.py ...
[PHASE-3] Add ChromaDB write to reporter_agent.py ...
```

This stops Copilot from adding Phase 4 code when you are in Phase 1.

---

## What Copilot Must NEVER Do

- Use `print()` for logging — use `logger`
- Hardcode any URL, token, or credential
- Import one agent from another agent
- Call `graph.invoke()` inside an agent — only `run.py` does this
- Use `asyncio` in Phase 1–3
- Skip type hints on any function
- Write `except Exception: pass` — always log to state
- Add packages to code without adding to `requirements.txt`
- Create files outside the defined folder structure
- Write Playwright scripts without loading a recording file first

