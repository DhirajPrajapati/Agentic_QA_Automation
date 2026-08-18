# Phase 5 + 6 Master Prompt
## Run on office laptop only — after Phase 4 is complete and repo is pushed

---

```
You are helping me complete Phase 5 (GitHub Actions trigger) and Phase 6
(server deployment) of the QA Orchestrator.
Phases 1–4 are complete. This work happens on the office laptop.
Read CLAUDE.md before any code.

## PHASE 5 SCOPE:
Goal: PR merge to UAT branch auto-triggers the system.
Real Jira comment posted. USE_MOCK=false.

## Task 1: .github/workflows/qa-trigger.yml

Create a GitHub Actions workflow file:

name: Agentic QA Trigger

on:
  pull_request:
    types: [closed]
    branches:
      - uat

jobs:
  qa-trigger:
    name: Run QA Orchestrator
    if: github.event.pull_request.merged == true
    runs-on: self-hosted

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium

      - name: Install Newman
        run: npm install -g newman

      - name: Extract Jira ID from branch name
        id: extract_jira
        run: |
          BRANCH="${{ github.head_ref }}"
          echo "Branch: $BRANCH"
          JIRA_ID=$(echo "$BRANCH" | grep -oP '[A-Z]+-[0-9]+' | head -1)
          if [ -z "$JIRA_ID" ]; then
            echo "ERROR: No Jira ID found in branch name: $BRANCH"
            echo "Branch must follow format: feature/PROJ-123-description"
            exit 1
          fi
          echo "Extracted Jira ID: $JIRA_ID"
          echo "jira_id=$JIRA_ID" >> $GITHUB_OUTPUT

      - name: Run QA Orchestrator
        env:
          USE_MOCK: "false"
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }}
          CONFLUENCE_EMAIL: ${{ secrets.CONFLUENCE_EMAIL }}
          CONFLUENCE_API_TOKEN: ${{ secrets.CONFLUENCE_API_TOKEN }}
          UAT_BASE_URL: ${{ secrets.UAT_BASE_URL }}
          CHROMADB_PATH: ./memory/chromadb
        run: |
          python run.py --jira ${{ steps.extract_jira.outputs.jira_id }}

      - name: Upload test artifacts on failure
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: qa-failure-artifacts
          path: |
            outputs/screenshots/
            outputs/reports/
          retention-days: 7

Add these to GitHub repo Secrets (Settings → Secrets → Actions):
- OPENAI_API_KEY
- JIRA_BASE_URL
- JIRA_EMAIL
- JIRA_API_TOKEN
- CONFLUENCE_BASE_URL
- CONFLUENCE_EMAIL
- CONFLUENCE_API_TOKEN
- UAT_BASE_URL

## Task 2: Self-Hosted Runner Setup

On office laptop, run these commands:
(Get the exact token from GitHub → Settings → Actions → Runners → New runner)

mkdir actions-runner && cd actions-runner
# Download runner (GitHub will give you the exact URL)
# Configure:
./config.sh --url https://github.com/YOUR_ORG/qa-orchestrator --token YOUR_TOKEN
# Install as service (runs on startup):
sudo ./svc.sh install
sudo ./svc.sh start

## Task 3: Branch Naming Enforcement

Add a branch protection note in README.md:
Branches MUST follow: {type}/{JIRA-ID}-{description}
Examples:
  feature/PROJ-123-investor-otp-fix
  bugfix/PROJ-456-redemption-error

## Task 4: Office Laptop .env

Set these values (USE_MOCK=false):
USE_MOCK=false
OPENAI_API_KEY=<real key>
JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.office.email@company.com
JIRA_API_TOKEN=<real token>
CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net
CONFLUENCE_EMAIL=your.office.email@company.com
CONFLUENCE_API_TOKEN=<real token>
UAT_BASE_URL=https://uat.yourportal.com
CHROMADB_PATH=./memory/chromadb

## Task 5: Manual Test Before Activating Actions

python run.py --jira REAL-PROJ-123

Verify:
- Real Jira ticket receives a comment
- Email sent to QA team
- No errors in console
- Exit code 0 (echo $?)

## Phase 5 Validation:

1. Merge a test PR:
   - Create branch: feature/PROJ-123-test-qa-system
   - Make a trivial change (update README.md)
   - Open PR → UAT branch
   - Merge it
   - Watch GitHub Actions tab

2. Check Actions tab — run must:
   - Show "Extracted Jira ID: PROJ-123"
   - Complete without red X
   - Take < 8 minutes total

3. Check Jira ticket PROJ-123:
   - Must have a new comment from the bot
   - Comment must have the correct table structure

---

## PHASE 6 SCOPE (Optional):
Goal: 24/7 server operation. Office laptop not required.

## Task 1: Dockerfile

Create Dockerfile in project root:

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    nodejs npm \
    && rm -rf /var/lib/apt/lists/*

# Install Newman
RUN npm install -g newman

# Copy requirements first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browser
RUN playwright install chromium
RUN playwright install-deps chromium

# Copy project
COPY . .

# Create output directories
RUN mkdir -p outputs/scripts outputs/collections outputs/reports outputs/screenshots

# Entry point
ENTRYPOINT ["python", "run.py"]

## Task 2: docker-compose.yml

version: "3.9"

services:
  qa-orchestrator:
    build: .
    environment:
      USE_MOCK: "false"
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      JIRA_BASE_URL: ${JIRA_BASE_URL}
      JIRA_EMAIL: ${JIRA_EMAIL}
      JIRA_API_TOKEN: ${JIRA_API_TOKEN}
      CONFLUENCE_BASE_URL: ${CONFLUENCE_BASE_URL}
      CONFLUENCE_EMAIL: ${CONFLUENCE_EMAIL}
      CONFLUENCE_API_TOKEN: ${CONFLUENCE_API_TOKEN}
      UAT_BASE_URL: ${UAT_BASE_URL}
      CHROMADB_PATH: /app/memory/chromadb
    volumes:
      - ./memory:/app/memory
      - ./outputs:/app/outputs
      - ./recordings:/app/recordings
      - ./postman_collections:/app/postman_collections
    network_mode: host

  # Optional: separate ChromaDB server for production
  # chromadb:
  #   image: chromadb/chroma:latest
  #   ports:
  #     - "8000:8000"
  #   volumes:
  #     - ./memory/chromadb:/chroma/chroma

## Phase 6 Validation:

docker build -t qa-orchestrator .
docker run --env-file .env qa-orchestrator --jira PROJ-123

# Run 5 consecutive automated runs:
for i in 1 2 3 4 5; do
  echo "=== Run $i ==="
  docker run --env-file .env -v ./memory:/app/memory qa-orchestrator --jira PROJ-123
  echo "Exit: $?"
done

All 5 must complete with exit code 0.
After restart, ChromaDB must still have all learnings:
docker run --env-file .env -v ./memory:/app/memory qa-orchestrator --jira PROJ-123
# Must show: "[orchestrator] Retrieved N past learnings from ChromaDB" where N > 0
```

