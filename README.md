# QA Orchestrator

An agentic QA automation system built on LangGraph that reads a Jira
ticket, pulls module knowledge from Confluence, and generates test cases,
UI scripts, and API collections — with everything mocked locally until
real credentials are available.

## Why

Manual QA on a ticket typically takes 1–2 days and produces inconsistent
test coverage that depends on which engineer picks it up. This pipeline
turns that into a ~5 minute automated run: same standard every time,
regression + API coverage on every ticket, and selectors that self-heal
instead of silently rotting.

## How it works

1. **Orchestrator** reads the Jira ticket, resolves the module, pulls the
   matching Confluence page, and queries ChromaDB for past failures on
   that module.
2. **Analysis agent** turns that context into a prioritised list of flows
   to test, risk areas, and which user types are in scope.
3. **Test case agent** writes structured, human-readable test cases
   (happy path, negative, edge, API).
4. **Test script agent** turns those into executable code — Playwright UI
   scripts built on top of a *recorded* baseline (never hallucinated
   selectors) and Postman API collections built on top of the BE team's
   real collection.
5. **Playwright agent** runs the UI tests. If a selector breaks, an
   internal self-healing subgraph screenshots the DOM, asks the LLM for
   alternative selectors, and retries before giving up.
6. **API agent** runs the Postman collection via Newman.
7. **Reporter agent** posts a pass/fail summary to Jira and email, and
   writes what it learned (failures, healed selectors, flaky patterns)
   back to ChromaDB for the next run.

All state passes between agents through a single shared `QAState` object —
no agent calls another agent directly, so each one is testable in
isolation and the state at any point is fully inspectable.

## Mock vs. real

Every external dependency (Jira, Confluence, Playwright's browser
execution, Jira/email reporting) is mocked locally via files under
`mock_data/` when `USE_MOCK=true`. Flipping it to `false` and supplying
real credentials in `.env` is the only change needed to run against real
systems — no code changes. ChromaDB is always real; it runs locally with
no credentials required.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
cp .env.example .env   # defaults already work with no API key
python run.py --jira PROJ-123
```

## Current phase

**Phase 1** — reads mock Jira + Confluence data and prints generated test
cases to the terminal. `USE_MOCK=true` and `USE_MOCK_LLM=true` in `.env`
mean this runs end-to-end with no external credentials at all; set
`USE_MOCK_LLM=false` once a real `OPENAI_API_KEY` is available.

## Project layout

```
agents/     one file per pipeline stage (orchestrator, analysis, test case,
            test script, playwright, api, reporter)
graph/      LangGraph state definition, graph wiring, conditional edges
tools/      clients for Jira, Confluence, ChromaDB, recordings, collections, LLM
recordings/ real Playwright selector baselines per user type
postman_collections/  BE-provided API collections per user type
mock_data/  local stand-ins for Jira, Confluence, ChromaDB seed data
config/     module → Confluence/recording mapping, Postman environments
tests/      unit tests per agent/tool
docs/       full architecture write-up (start at docs/01_overview.md)
```

See [docs/](./docs/README.md) for the full architecture, agent
specifications, and end-to-end workflow walkthrough.
