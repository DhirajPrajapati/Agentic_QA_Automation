# 09 — Phased Delivery Plan
## Agentic QA Automation System

---

## Phase Overview

```mermaid
flowchart LR
    P1([Phase 1\nCore Loop]) --> P2([Phase 2\nUI Execution]) --> P3([Phase 3\nSelf-Learning]) --> P4([Phase 4\nFull Pipeline]) --> P5([Phase 5\nAuto Trigger]) --> P6([Phase 6\nServer Deploy])

    style P1 fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style P2 fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style P3 fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style P4 fill:#FAEEDA,stroke:#854F0B,color:#412402
    style P5 fill:#E6F1FB,stroke:#185FA5,color:#042C53
    style P6 fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
```

**Golden rule: Get the core loop working before adding features. Each phase is independently valuable.**

---

## Phase 1 — Core Loop

```mermaid
graph TD
    subgraph P1["Phase 1 — Core Loop (1–2 weeks)"]
        A[run.py + CLI] --> B[Jira REST client]
        B --> C[Confluence REST client]
        C --> D[module_map.json]
        D --> E[orchestrator_agent\nbasic linear flow]
        E --> F[analysis_agent]
        F --> G[test_case_agent]
        G --> H[Print test cases\nto terminal]
    end

    style P1 fill:#E1F5EE,stroke:#0F6E56
```

**Validation:**
```bash
python run.py --jira PROJ-123
# Output: list of relevant test cases printed to terminal
```

**Success criteria:** Test cases are relevant to the Jira ticket and reference correct Confluence knowledge.

**What's NOT built yet:** Playwright, API testing, ChromaDB, GitHub Actions

---

## Phase 2 — UI Script Generation and Execution

```mermaid
graph TD
    subgraph P2["Phase 2 — UI Execution (1–2 weeks)"]
        A[Record happy paths\nVS Code Playwright extension]
        A --> B[recordings/ folder populated]
        B --> C[test_script_agent\nUI script generation]
        C --> D[playwright_agent\nbasic execution]
        D --> E[Pass/fail logged\nto terminal]
        E --> F[Screenshots saved\nto outputs/]
    end

    style P2 fill:#E1F5EE,stroke:#0F6E56
```

**Validation:** At least 3 test cases run end-to-end without manual intervention.

**What's NOT built yet:** Self-healing, API testing, ChromaDB, reporting

---

## Phase 3 — Self-Healing and ChromaDB Memory

```mermaid
graph TD
    subgraph P3["Phase 3 — Self-Learning (1–2 weeks)"]
        A[chromadb_client.py] --> B[seed_chromadb.py\nload Section 11 known issues]
        B --> C[ChromaDB RAG query\nin orchestrator_agent]
        C --> D[Self-healing subgraph\nin playwright_agent]
        D --> E[ChromaDB write\non healing success]
        E --> F[reporter_agent\nChromaDB reflection write]
    end

    style P3 fill:#EEEDFE,stroke:#534AB7
```

**Validation sequence:**
```mermaid
sequenceDiagram
    participant Run1 as Run 1
    participant CDB as ChromaDB
    participant Run2 as Run 2

    Run1->>Run1: Selector fails → self-heal fires
    Run1->>CDB: Write healed selector
    Run2->>CDB: Query past learnings
    CDB-->>Run2: Return healed selector
    Run2->>Run2: Use healed selector directly
    Note over Run2: No self-healing needed on Run 2 ✓
```

---

## Phase 4 — API Testing and Full Reporting

```mermaid
graph TD
    subgraph P4["Phase 4 — Full Pipeline (1–2 weeks)"]
        A[BE team provides\nPostman collections] --> B[api_agent\nNewman execution]
        B --> C[test_script_agent\nAPI script generation]
        C --> D[Conditional routing\nskip_api logic]
        D --> E[reporter_agent\nJira comment + email]
        E --> F[Full end-to-end\npipeline complete]
    end

    style P4 fill:#FAEEDA,stroke:#854F0B
```

**Validation:** Jira ticket receives structured comment within 6 minutes of triggering. Both UI and API results present.

---

## Phase 5 — GitHub Actions Auto-Trigger

```mermaid
graph TD
    subgraph P5["Phase 5 — Auto Trigger (3–5 days)"]
        A[qa-trigger.yml\nGitHub Actions workflow]
        B[Self-hosted runner setup\non developer machine]
        C[Branch name extraction\nJira ID parsing]
        D[Exit code handling\n0=pass 1=fail in run.py]
        A --> B --> C --> D
    end

    style P5 fill:#E6F1FB,stroke:#185FA5
```

```yaml
# .github/workflows/qa-trigger.yml
name: Agentic QA Trigger
on:
  pull_request:
    types: [closed]
    branches: [uat]

jobs:
  qa-trigger:
    if: github.event.pull_request.merged == true
    runs-on: self-hosted
    steps:
      - name: Extract Jira ID
        run: |
          BRANCH="${{ github.head_ref }}"
          JIRA_ID=$(echo "$BRANCH" | grep -oP '[A-Z]+-[0-9]+')
          echo "jira_id=$JIRA_ID" >> $GITHUB_OUTPUT
      - name: Run QA Orchestrator
        run: python run.py --jira ${{ steps.extract.outputs.jira_id }}
```

---

## Phase 6 — Server Deployment

```mermaid
graph TD
    subgraph P6["Phase 6 — Server (1 week)"]
        A[Dockerfile] --> B[docker-compose.yml]
        B --> C[qa-orchestrator container]
        B --> D[ChromaDB server container]
        C --> E[Self-hosted GH runner\non server process]
        D --> F[Persistent ChromaDB\nacross restarts]
    end

    style P6 fill:#FAECE7,stroke:#993C1D
```

---

## Delivery Timeline

```mermaid
gantt
    title QA Orchestrator — Estimated Build Timeline
    dateFormat  YYYY-MM-DD
    axisFormat  %b %d

    section Phase 1
    Project scaffold + Jira + Confluence    :p1a, 2025-01-01, 7d
    Orchestrator + analysis + test cases    :p1b, after p1a, 7d

    section Phase 2
    Record happy paths                      :p2a, after p1b, 3d
    test_script_agent + playwright_agent    :p2b, after p2a, 11d

    section Phase 3
    ChromaDB setup + seed                   :p3a, after p2b, 4d
    Self-healing subgraph                   :p3b, after p3a, 7d
    Reflection write                        :p3c, after p3b, 3d

    section Phase 4
    api_agent + Newman                      :p4a, after p3c, 7d
    reporter_agent full                     :p4b, after p4a, 7d

    section Phase 5
    GitHub Actions workflow                 :p5, after p4b, 5d

    section Phase 6
    Docker + server deploy                  :p6, after p5, 7d
```

---

## Value at Each Phase

```mermaid
xychart-beta
    title "Business Value Delivered Per Phase"
    x-axis ["Phase 1", "Phase 2", "Phase 3", "Phase 4", "Phase 5", "Phase 6"]
    y-axis "Value delivered %" 0 --> 100
    bar [20, 50, 70, 90, 96, 100]
```

Even Phase 1 + Phase 2 alone is more impressive than most AI engineering portfolio projects. Phase 3 (self-learning) is the differentiating feature that makes this system genuinely novel.

---

## If Time is Limited — Minimum Viable System

```mermaid
flowchart LR
    A[Phase 1\nCore intelligence] --> B[Phase 2\nUI automation] --> C[Phase 3\nSelf-learning]
    C --> D([Portfolio-ready\ndemonstration])

    style A fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style B fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style C fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style D fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

Phases 1–3 in approximately 5 weeks produces a system that: reads Jira tickets, fetches Confluence knowledge, generates test cases, runs Playwright tests, self-heals broken selectors, and grows smarter with every run. That is a complete, demonstrable, senior AI engineering deliverable.

---

*Next: [10_team_conventions.md](./10_team_conventions.md) — Team rules and conventions*
