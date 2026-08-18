# Phase 5 + 6 Master Prompt — Azure OpenAI Version

## Run on office laptop only — after Phase 4 is complete and repo is pushed

---

```
You are helping me complete Phase 5 (GitHub Actions trigger) and Phase 6
(server deployment) of the QA Orchestrator on the office laptop.
Phases 1–4 are complete on personal laptop.
This project uses Azure OpenAI — NOT standard OpenAI.
Read CLAUDE.md before any code.

==============================================================
PHASE 5 — GitHub Actions Auto-Trigger (Office Laptop Only)
==============================================================

Goal: PR merge to UAT branch auto-triggers the system.
Real Jira comment posted. USE_MOCK=false. USE_MOCK_LLM=false.
LLM_PROVIDER=azure.

## Task 1: .github/workflows/qa-trigger.yml

Create this exact file:

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

      - name: Install Python dependencies
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
            echo "ERROR: No Jira ID found in branch: $BRANCH"
            echo "Branch must follow: feature/PROJ-123-description"
            exit 1
          fi
          echo "Extracted Jira ID: $JIRA_ID"
          echo "jira_id=$JIRA_ID" >> $GITHUB_OUTPUT

      - name: Run QA Orchestrator
        env:
          USE_MOCK: "false"
          USE_MOCK_LLM: "false"
          LLM_PROVIDER: "azure"
          AZURE_OPENAI_API_KEY: ${{ secrets.AZURE_OPENAI_API_KEY }}
          AZURE_OPENAI_ENDPOINT: ${{ secrets.AZURE_OPENAI_ENDPOINT }}
          AZURE_OPENAI_DEPLOYMENT_NAME: ${{ secrets.AZURE_OPENAI_DEPLOYMENT_NAME }}
          AZURE_OPENAI_API_VERSION: "2024-02-01"
          JIRA_BASE_URL: ${{ secrets.JIRA_BASE_URL }}
          JIRA_EMAIL: ${{ secrets.JIRA_EMAIL }}
          JIRA_API_TOKEN: ${{ secrets.JIRA_API_TOKEN }}
          CONFLUENCE_BASE_URL: ${{ secrets.CONFLUENCE_BASE_URL }}
          CONFLUENCE_EMAIL: ${{ secrets.CONFLUENCE_EMAIL }}
          CONFLUENCE_API_TOKEN: ${{ secrets.CONFLUENCE_API_TOKEN }}
          UAT_BASE_URL: ${{ secrets.UAT_BASE_URL }}
          CHROMADB_PATH: ./memory/chromadb
          SMTP_HOST: ${{ secrets.SMTP_HOST }}
          SMTP_PORT: ${{ secrets.SMTP_PORT }}
          SMTP_USER: ${{ secrets.SMTP_USER }}
          SMTP_PASSWORD: ${{ secrets.SMTP_PASSWORD }}
          EMAIL_RECIPIENTS: ${{ secrets.EMAIL_RECIPIENTS }}
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

## Task 2: GitHub Repository Secrets

Add ALL of these in GitHub → Settings → Secrets → Actions:

Azure OpenAI (get from your org's Azure portal):
  AZURE_OPENAI_API_KEY          your Azure OpenAI key
  AZURE_OPENAI_ENDPOINT         https://your-resource.openai.azure.com/
  AZURE_OPENAI_DEPLOYMENT_NAME  gpt-4o (confirm exact name with org)

Jira:
  JIRA_BASE_URL                 https://yourcompany.atlassian.net
  JIRA_EMAIL                    your.email@company.com
  JIRA_API_TOKEN                your Jira API token

Confluence:
  CONFLUENCE_BASE_URL           https://yourcompany.atlassian.net
  CONFLUENCE_EMAIL              your.email@company.com
  CONFLUENCE_API_TOKEN          your Confluence API token

UAT:
  UAT_BASE_URL                  https://uat.yourportal.com

Email (optional — for email reporting):
  SMTP_HOST                     smtp.yourcompany.com
  SMTP_PORT                     587
  SMTP_USER                     qa-reports@yourcompany.com
  SMTP_PASSWORD                 your smtp password
  EMAIL_RECIPIENTS              qa@yourcompany.com

## Task 3: Self-Hosted Runner Setup

On office laptop terminal — get the exact token from:
GitHub repo → Settings → Actions → Runners → New self-hosted runner

mkdir actions-runner && cd actions-runner
# GitHub will give you the exact download URL for your OS
# After downloading and extracting:
./config.sh --url https://github.com/YOUR_ORG/qa-orchestrator --token YOUR_TOKEN
sudo ./svc.sh install
sudo ./svc.sh start

Verify runner is online:
GitHub repo → Settings → Actions → Runners
Should show your machine as "Idle" with a green dot.

## Task 4: Office Laptop .env

Create .env on office laptop with these exact values:

USE_MOCK=false
USE_MOCK_LLM=false
LLM_PROVIDER=azure

AZURE_OPENAI_API_KEY=your_real_azure_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o
AZURE_OPENAI_API_VERSION=2024-02-01

JIRA_BASE_URL=https://yourcompany.atlassian.net
JIRA_EMAIL=your.office.email@company.com
JIRA_API_TOKEN=your_real_jira_token

CONFLUENCE_BASE_URL=https://yourcompany.atlassian.net
CONFLUENCE_EMAIL=your.office.email@company.com
CONFLUENCE_API_TOKEN=your_real_confluence_token

UAT_BASE_URL=https://uat.yourportal.com
CHROMADB_PATH=./memory/chromadb

SMTP_HOST=smtp.yourcompany.com
SMTP_PORT=587
SMTP_USER=qa-reports@yourcompany.com
SMTP_PASSWORD=your_smtp_password
EMAIL_RECIPIENTS=qa@yourcompany.com

## Task 5: Office Laptop Data Setup

Step 1 — Update config/module_map.json with real Confluence page IDs:
{
  "investor": {
    "login": "REAL_CONFLUENCE_PAGE_ID_HERE",
    "otp":   "REAL_CONFLUENCE_PAGE_ID_HERE",
    ...
  }
}
Get page IDs from Confluence URL: /wiki/spaces/SPACE/pages/PAGE_ID/Page+Name

Step 2 — Record happy paths using VS Code Playwright extension:
  - Open VS Code → Playwright extension → Record
  - Record investor login flow on UAT
  - Save to: recordings/investor/login_happy_path.py
  - Repeat for distributor and employee flows

Step 3 — Get Postman collections from BE team:
  - Ask BE team for module-wise Postman collections
  - Save to: postman_collections/investor/login.postman_collection.json
  - Ensure each collection has a pre-request auth script

Step 4 — Seed ChromaDB from Confluence Section 11 (Known Issues):
  python scripts/seed_chromadb.py

## Task 6: Manual Test Before Activating GitHub Actions

python run.py --jira REAL-PROJ-123

Verify all of these:
  - Real Jira ticket receives a structured comment
  - Email sent to QA team
  - ChromaDB learning written
  - Exit code 0: echo $?
  - No errors in console output

Fix any credential or API issues before moving to auto-trigger.

## Phase 5 Validation:

1. Merge a test PR to UAT:
   git checkout -b feature/PROJ-123-test-qa-system
   # Make a trivial change
   git commit -m "test: verify QA auto-trigger"
   git push origin feature/PROJ-123-test-qa-system
   # Open PR → base: uat → merge it

2. Watch GitHub Actions tab:
   Must show "Extracted Jira ID: PROJ-123"
   Must complete without red X
   Must finish within 8 minutes

3. Check Jira ticket PROJ-123:
   Must have new comment from the pipeline
   Comment must have the structured table format

Phase 5 complete when:
  - PR merge triggers run with zero manual steps
  - Jira comment appears within 8 minutes
  - Exit code 0 on all pass, exit code 1 on genuine failures

==============================================================
PHASE 6 — Server Deployment (Optional)
==============================================================

Goal: 24/7 operation. Office laptop not required to be on.

## Task 1: Dockerfile

Create in project root:

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

RUN npm install -g newman

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium
RUN playwright install-deps chromium

COPY . .

RUN mkdir -p outputs/scripts outputs/collections outputs/reports outputs/screenshots

ENTRYPOINT ["python", "run.py"]

## Task 2: docker-compose.yml

Create in project root:

version: "3.9"

services:
  qa-orchestrator:
    build: .
    environment:
      USE_MOCK: "false"
      USE_MOCK_LLM: "false"
      LLM_PROVIDER: "azure"
      AZURE_OPENAI_API_KEY: ${AZURE_OPENAI_API_KEY}
      AZURE_OPENAI_ENDPOINT: ${AZURE_OPENAI_ENDPOINT}
      AZURE_OPENAI_DEPLOYMENT_NAME: ${AZURE_OPENAI_DEPLOYMENT_NAME}
      AZURE_OPENAI_API_VERSION: ${AZURE_OPENAI_API_VERSION:-2024-02-01}
      JIRA_BASE_URL: ${JIRA_BASE_URL}
      JIRA_EMAIL: ${JIRA_EMAIL}
      JIRA_API_TOKEN: ${JIRA_API_TOKEN}
      CONFLUENCE_BASE_URL: ${CONFLUENCE_BASE_URL}
      CONFLUENCE_EMAIL: ${CONFLUENCE_EMAIL}
      CONFLUENCE_API_TOKEN: ${CONFLUENCE_API_TOKEN}
      UAT_BASE_URL: ${UAT_BASE_URL}
      CHROMADB_PATH: /app/memory/chromadb
      SMTP_HOST: ${SMTP_HOST}
      SMTP_PORT: ${SMTP_PORT:-587}
      SMTP_USER: ${SMTP_USER}
      SMTP_PASSWORD: ${SMTP_PASSWORD}
      EMAIL_RECIPIENTS: ${EMAIL_RECIPIENTS}
    volumes:
      - ./memory:/app/memory
      - ./outputs:/app/outputs
      - ./recordings:/app/recordings
      - ./postman_collections:/app/postman_collections
      - ./config:/app/config
    network_mode: host
    restart: unless-stopped

Note on ChromaDB in Docker:
- The ./memory volume mount persists ChromaDB data between container restarts
- ChromaDB runs in local persistent mode inside the container
- No separate ChromaDB server needed — same PersistentClient as Phase 1-5

## Phase 6 Validation:

# Build image
docker build -t qa-orchestrator .

# Test single run
docker run --env-file .env \
  -v $(pwd)/memory:/app/memory \
  -v $(pwd)/recordings:/app/recordings \
  -v $(pwd)/postman_collections:/app/postman_collections \
  qa-orchestrator --jira PROJ-123

# Run 5 consecutive runs — all must pass
for i in 1 2 3 4 5; do
  echo "=== Run $i ==="
  docker run --env-file .env \
    -v $(pwd)/memory:/app/memory \
    qa-orchestrator --jira PROJ-123
  echo "Exit code: $?"
done

# Verify ChromaDB persists after restart
docker run --env-file .env \
  -v $(pwd)/memory:/app/memory \
  qa-orchestrator --jira PROJ-123
# Must show: "[orchestrator] Retrieved N past learnings from ChromaDB" where N > 3

Phase 6 complete when:
  - 5 consecutive Docker runs complete with exit code 0
  - ChromaDB learnings persist between container restarts
  - Self-hosted GitHub Actions runner moved to server
  - System operates without office laptop being powered on

==============================================================
OFFICE LAPTOP MIGRATION — Exact Commands
==============================================================

# On personal laptop — push Phase 4 complete code
git add .
git commit -m "feat: Phase 4 complete — full pipeline with Azure OpenAI"
git push origin main

# On office laptop
git clone https://github.com/your-org/qa-orchestrator.git
cd qa-orchestrator

pip install -r requirements.txt
playwright install chromium
npm install -g newman

# Create .env with all real values (see Task 4 above)
cp .env.example .env
# Edit .env — fill all values, USE_MOCK=false, USE_MOCK_LLM=false

# Update Confluence page IDs
# Edit config/module_map.json with real page IDs

# Record happy paths
# Use VS Code Playwright extension → save to recordings/

# Get BE team Postman collections
# Save to postman_collections/

# Seed ChromaDB
python scripts/seed_chromadb.py

# Verify with real ticket
python run.py --jira REAL-PROJ-123

# Verify Jira comment appeared on the ticket
# Then proceed to GitHub Actions setup (Task 3 above)

Zero code changes. Config and files only.
The only difference between personal laptop and office laptop is .env values.
```
