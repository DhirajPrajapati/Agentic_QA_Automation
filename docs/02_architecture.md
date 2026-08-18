# 02 — System Architecture
## Agentic QA Automation System

---

## High-Level System Architecture

```mermaid
graph TB
    subgraph TRIGGER["🚀 Trigger Layer"]
        T1[PR merged to UAT]
        T2[Manual CLI\npython run.py]
        GH[GitHub Actions]
        T1 --> GH --> ENTRY
        T2 --> ENTRY[run.py\n--jira PROJ-123]
    end

    subgraph INPUT["📥 Input Layer"]
        JIRA[Jira REST API\nTicket + BRD + Labels]
        CONF[Confluence REST API\nModule Knowledge]
        CDB[ChromaDB RAG\nPast Learnings]
    end

    subgraph ORCH["🧠 Orchestration Layer"]
        OA[orchestrator_agent\nLangGraph Supervisor]
        STATE[(Shared State\nQAState)]
    end

    subgraph GEN["⚙️ Generation Layer"]
        AA[analysis_agent]
        TCA[test_case_agent]
        TSA[test_script_agent]
    end

    subgraph EXEC["▶️ Execution Layer"]
        PA[playwright_agent\n+ self-healing]
        APIA[api_agent\nNewman CLI]
    end

    subgraph REPORT["📊 Reporting Layer"]
        RA[reporter_agent]
        JC[Jira Comment]
        EM[Email Report]
        CW[ChromaDB Write]
    end

    ENTRY --> JIRA & CONF & CDB
    JIRA & CONF & CDB --> STATE
    STATE --> OA
    OA --> AA --> TCA --> TSA
    TSA --> PA & APIA
    PA & APIA --> RA
    RA --> JC & EM & CW

    style TRIGGER fill:#E1F5EE,stroke:#0F6E56
    style INPUT fill:#E6F1FB,stroke:#185FA5
    style ORCH fill:#EEEDFE,stroke:#534AB7
    style GEN fill:#E1F5EE,stroke:#0F6E56
    style EXEC fill:#FAECE7,stroke:#993C1D
    style REPORT fill:#FAEEDA,stroke:#854F0B
```

---

## LangGraph State Machine

```mermaid
stateDiagram-v2
    [*] --> initialise : run.py called

    initialise --> fetch_inputs : load .env config
    fetch_inputs --> build_state : Jira + Confluence + ChromaDB

    build_state --> orchestrator : state ready

    orchestrator --> analysis : plan decided
    analysis --> test_case_gen : scope defined
    test_case_gen --> script_gen : test cases written

    script_gen --> ui_exec : UI scripts ready
    script_gen --> api_exec : Postman collection ready

    ui_exec --> self_heal : selector fails
    self_heal --> ui_exec : retry with new selector
    self_heal --> genuine_failure : all alternatives exhausted

    ui_exec --> results_merge : all tests done
    api_exec --> results_merge : Newman complete
    genuine_failure --> results_merge : logged as failure

    results_merge --> reporter : combined results
    reporter --> chromadb_write : Jira + email sent
    chromadb_write --> [*] : learnings stored
```

---

## Component Relationships

```mermaid
graph LR
    subgraph External["External Systems"]
        JIRA_API[Jira API]
        CONF_API[Confluence API]
        UAT[UAT Portal]
        SMTP[SMTP Server]
    end

    subgraph Core["Core System"]
        OA[orchestrator_agent]
        AA[analysis_agent]
        TCA[test_case_agent]
        TSA[test_script_agent]
        PA[playwright_agent]
        APIA[api_agent]
        RA[reporter_agent]
    end

    subgraph Storage["Local Storage"]
        CDB[(ChromaDB)]
        REC[recordings/]
        PCO[postman_collections/]
        OUT[outputs/]
    end

    OA -->|fetch ticket| JIRA_API
    OA -->|fetch knowledge| CONF_API
    OA -->|query past failures| CDB

    TSA -->|load recording| REC
    TSA -->|load collection| PCO

    PA -->|run browser| UAT
    APIA -->|run Newman| UAT

    PA -->|screenshots| OUT
    TSA -->|generated scripts| OUT

    RA -->|post comment| JIRA_API
    RA -->|send email| SMTP
    RA -->|store learnings| CDB

    style External fill:#F1EFE8,stroke:#5F5E5A
    style Core fill:#EEEDFE,stroke:#534AB7
    style Storage fill:#E1F5EE,stroke:#0F6E56
```

---

## LangGraph Shared State Object

```mermaid
classDiagram
    class QAState {
        +String jira_id
        +Dict jira_data
        +String confluence_context
        +List past_failures
        +List test_cases
        +String ui_scripts
        +Dict api_collection
        +Dict ui_results
        +Dict api_results
        +String status
        +Int retry_count
        +Bool skip_api
        +List errors
    }

    class orchestrator_agent {
        +reads: jira_id
        +writes: jira_data, confluence_context, past_failures
    }
    class analysis_agent {
        +reads: jira_data, confluence_context, past_failures
        +writes: test_scope, skip_api
    }
    class test_case_agent {
        +reads: jira_data, confluence_context, test_scope
        +writes: test_cases
    }
    class test_script_agent {
        +reads: test_cases, confluence_context
        +writes: ui_scripts, api_collection
    }
    class playwright_agent {
        +reads: ui_scripts, past_failures
        +writes: ui_results
    }
    class api_agent {
        +reads: api_collection, skip_api
        +writes: api_results
    }
    class reporter_agent {
        +reads: ui_results, api_results, test_cases
        +writes: ChromaDB, Jira, Email
    }

    QAState --> orchestrator_agent
    QAState --> analysis_agent
    QAState --> test_case_agent
    QAState --> test_script_agent
    QAState --> playwright_agent
    QAState --> api_agent
    QAState --> reporter_agent
```

---

## Trigger Flow — Local vs Server

```mermaid
sequenceDiagram
    participant Dev as Developer
    participant GH as GitHub
    participant GA as GitHub Actions
    participant Runner as Self-Hosted Runner
    participant QA as QA Orchestrator

    Note over Dev,QA: Phase 1–4: Local trigger
    Dev->>QA: python run.py --jira PROJ-123
    QA->>QA: Load .env + build state
    QA->>QA: Run full pipeline

    Note over Dev,QA: Phase 5+: Automatic trigger
    Dev->>GH: git push feature/PROJ-123-fix
    Dev->>GH: Open PR → UAT
    Dev->>GH: Merge PR
    GH->>GA: pull_request.closed event fires
    GA->>GA: Extract PROJ-123 from branch name
    GA->>Runner: Dispatch job to self-hosted runner
    Runner->>QA: python run.py --jira PROJ-123
    QA->>QA: Run full pipeline
    QA-->>GH: Post results to Jira
```

---

## Data Flow Summary

```mermaid
flowchart LR
    A[Jira Ticket\nBRD + Labels] --> S[(Shared State)]
    B[Confluence Page\nModule Knowledge] --> S
    C[ChromaDB\nPast Learnings] --> S

    S --> D[analysis_agent\nScope decision]
    D --> E[test_case_agent\nHuman test cases]
    E --> F[test_script_agent\nExecutable scripts]

    REC[recordings/*.py\nReal selectors] --> F
    PC[postman_collections/*.json\nReal endpoints] --> F

    F --> G[playwright_agent\nUI execution]
    F --> H[api_agent\nAPI execution]

    G --> I[reporter_agent]
    H --> I

    I --> J[Jira Comment]
    I --> K[Email Report]
    I --> L[ChromaDB Learning]

    style S fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style REC fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style PC fill:#E6F1FB,stroke:#185FA5,color:#042C53
    style L fill:#EEEDFE,stroke:#534AB7,color:#26215C
```

---

*Next: [03_agents.md](./03_agents.md) — All 7 agents in detail*
