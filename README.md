# QA Orchestrator

An agentic QA automation system built on LangGraph that reads a Jira
ticket, pulls module knowledge from Confluence, and generates test cases,
UI scripts, and API collections — with everything mocked locally until
real credentials are available.

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
