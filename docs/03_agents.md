# 03 — Agent Specifications
## Agentic QA Automation System

---

## Agent Roster

```mermaid
graph TB
    subgraph Orchestration
        OA[🧠 orchestrator_agent\nLangGraph supervisor]
    end

    subgraph Generation
        AA[🔍 analysis_agent\nScope setter]
        TCA[📝 test_case_agent\nTest writer]
        TSA[⚙️ test_script_agent\nScript generator]
    end

    subgraph Execution
        PA[🎭 playwright_agent\nUI executor]
        APIA[🔌 api_agent\nAPI executor]
    end

    subgraph Reporting
        RA[📊 reporter_agent\nResults + memory]
    end

    OA --> AA --> TCA --> TSA
    TSA --> PA
    TSA --> APIA
    PA --> RA
    APIA --> RA

    style Orchestration fill:#EEEDFE,stroke:#534AB7
    style Generation fill:#E1F5EE,stroke:#0F6E56
    style Execution fill:#FAECE7,stroke:#993C1D
    style Reporting fill:#FAEEDA,stroke:#854F0B
```

---

## Agent 1 — `orchestrator_agent`

**Role:** Director. Controls the entire pipeline without executing any tests.

```mermaid
flowchart TD
    A[Receives jira_id] --> B[Fetch Jira ticket]
    B --> C[Resolve module from labels]
    C --> D[Fetch Confluence page]
    D --> E[Query ChromaDB for past failures]
    E --> F[Build shared state]
    F --> G[LLM Planner runs]
    G --> H{What to test?}
    H -->|FE + BE| I[Delegate to all agents]
    H -->|FE only| J[Skip api_agent]
    H -->|Blocker found| K[Go straight to reporter]
    I --> L[Monitor results]
    L --> M{All done?}
    M -->|Pass or fail| N[Hand off to reporter_agent]
    M -->|Agent error| O[Retry or escalate]

    style G fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style H fill:#FAEEDA,stroke:#854F0B,color:#412402
```

**Key decisions the orchestrator makes:**

```mermaid
graph LR
    L1[Labels: investor, login, otp] --> R1[Fetch investor/login Confluence page]
    L2[Labels: investor, login, dashboard] --> R2[Fetch 2 pages — merge context]
    L3[Labels: frontend only] --> R3[Set skip_api = true]
    L4[Labels: backend only] --> R4[Skip playwright_agent]
```

---

## Agent 2 — `analysis_agent`

**Role:** Reads all context and defines exactly what needs testing.

```mermaid
flowchart LR
    A[jira_data\nBRD + criteria] --> D[analysis_agent]
    B[confluence_context\nModule knowledge] --> D
    C[past_failures\nChromaDB results] --> D
    D --> E[Flows to test\nprioritised list]
    D --> F[Risk areas\nflaky + known issues]
    D --> G[skip_api flag\ntrue or false]
    D --> H[User types\nin scope]
```

**Output example:**
```
Flows: [standard_login P1, otp_new_device P1, otp_verify P1, otp_expiry P2]
Risk areas: ["OTP screen load slow", "Login button label may change"]
API in scope: true
User types: [retail_investor, institutional_investor]
```

---

## Agent 3 — `test_case_agent`

**Role:** Writes human-readable test cases. No code. Just structured test intent.

```mermaid
flowchart TD
    A[Analysis scope] --> B[test_case_agent]
    C[Confluence Section 6\nError messages exact text] --> B
    D[Confluence Section 7\nAPI endpoints] --> B

    B --> E[Happy path cases\nP1 priority]
    B --> F[Negative flow cases\nP2 priority]
    B --> G[Edge cases\nP3 priority]
    B --> H[API test cases\nif in scope]

    style B fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

**Test case format:**
```
TC-001 | Standard investor login | P1
Given:  User is on /investor/login
When:   Valid email + password entered → Login clicked
Then:   Redirected to /investor/dashboard
And:    Welcome banner visible
And:    Session token set in cookies
```

---

## Agent 4 — `test_script_agent`

**Role:** Converts test cases into executable code using real baselines — never invents selectors.

```mermaid
flowchart TD
    A[test_cases\nfrom test_case_agent] --> TSA[test_script_agent]
    B{Recording\nexists?} --> |Yes| C[Load recordings/investor/\nlogin_happy_path.py\nReal selectors]
    B --> |No| D[Use Confluence Section 8\nSelector hints as fallback]
    C --> TSA
    D --> TSA

    E{Postman collection\nexists?} --> |Yes| F[Load BE team\ncollection JSON]
    E --> |No| G[LLM generates\nAPI requests]
    F --> TSA
    G --> TSA

    TSA --> H[Enhanced Playwright .py\nAssertions + negative variants]
    TSA --> I[Enhanced Postman JSON\nNegative cases + env vars]

    style C fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style F fill:#E6F1FB,stroke:#185FA5,color:#042C53
    style TSA fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

**What the LLM adds on top of recordings:**

```mermaid
graph LR
    REC[Recording\nhappy path skeleton] --> PLUS[+]
    LLM[LLM adds] --> PLUS
    PLUS --> OUT[Complete test file]

    LLM --> A1[expect assertions\nat each checkpoint]
    LLM --> A2[Negative variants\nsame selectors, bad data]
    LLM --> A3[Data-driven loops\nall user types]
    LLM --> A4[Explicit waits\nfor known slow screens]
```

---

## Agent 5 — `playwright_agent`

**Role:** Runs UI tests with an internal self-healing subgraph for broken selectors.

```mermaid
flowchart TD
    A[Run Playwright script] --> B{Test passes?}
    B --> |Yes| C[Log PASS\ncontinue]
    B --> |Selector fails| D[SELF-HEALING FIRES]

    subgraph SH[Self-Healing Subgraph]
        D --> E[Screenshot current DOM]
        E --> F[LLM receives:\nscreenshot + failed selector\n+ test intent]
        F --> G[LLM suggests\n3 alternative selectors]
        G --> H[Try alternative 1]
        H --> |Pass| I[Write healed selector\nto ChromaDB]
        H --> |Fail| J[Try alternative 2]
        J --> |Pass| I
        J --> |Fail| K[Try alternative 3]
        K --> |Pass| I
        K --> |Fail| L[Genuine failure\nlog with screenshot]
    end

    I --> M[Continue test\nnext step]
    L --> N[Mark TC as FAIL\ncontinue other tests]
    C --> O{More tests?}
    M --> O
    N --> O
    O --> |Yes| A
    O --> |No| P[Write ui_results to state]

    style SH fill:#EEEDFE,stroke:#534AB7
    style I fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style L fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
```

**Result states:**

| Status | Meaning |
|---|---|
| `pass` | Test ran and all assertions passed |
| `fail` | Genuine failure — not a selector issue |
| `healed` | Selector fixed automatically — test passed after healing |
| `skip` | Test skipped due to prerequisite failure |

---

## Agent 6 — `api_agent`

**Role:** Runs Newman CLI against BE-provided Postman collections.

```mermaid
sequenceDiagram
    participant OA as orchestrator
    participant AG as api_agent
    participant NW as Newman CLI
    participant UAT as UAT API

    OA->>AG: api_collection + skip_api flag
    AG->>AG: Check skip_api
    alt skip_api is true
        AG-->>OA: Exit — FE only ticket
    else skip_api is false
        AG->>AG: Write enhanced collection to temp file
        AG->>NW: newman run collection.json --env uat.json
        NW->>UAT: POST /investor/login
        UAT-->>NW: 200 { token, is_new_device: true }
        NW->>UAT: POST /investor/verify-otp
        UAT-->>NW: 200 { auth_token }
        NW->>UAT: POST /verify-otp (expired)
        UAT-->>NW: 410 { error: otp_expired }
        NW-->>AG: JSON report
        AG->>AG: Parse report → map to test case IDs
        AG-->>OA: api_results written to state
    end
```

**Why Newman over raw HTTP:**

```mermaid
graph TD
    A[BE Team Postman Collection] --> B[Newman CLI]
    B --> C[Session management ✓]
    B --> D[Cookie chains ✓]
    B --> E[Pre-request auth scripts ✓]
    B --> F[Structured JSON report ✓]
    B --> G[No custom code needed ✓]

    style A fill:#E6F1FB,stroke:#185FA5,color:#042C53
    style B fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

---

## Agent 7 — `reporter_agent`

**Role:** Compiles results, posts to Jira and email, writes learnings to ChromaDB.

```mermaid
flowchart TD
    A[ui_results] --> RA[reporter_agent]
    B[api_results] --> RA
    C[test_cases] --> RA
    D[jira_data] --> RA

    RA --> E[Compile summary\npass/fail table]
    E --> F[Post Jira comment\nwith full details]
    E --> G[Send email report\nto QA team]
    E --> H[Write reflection doc\nto ChromaDB]

    H --> I[What failed + why]
    H --> J[Healed selectors]
    H --> K[Flaky patterns detected]
    H --> L[Deployment changes spotted]

    style RA fill:#FAEEDA,stroke:#854F0B,color:#412402
    style H fill:#EEEDFE,stroke:#534AB7,color:#26215C
```

**Jira comment structure:**

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agentic QA Report — PROJ-123
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UI Tests:  5/5 PASS (1 auto-healed)
API Tests: 3/3 PASS

✅ TC-001  Standard login
✅ TC-002  OTP trigger on new device
✅ TC-003  OTP verification
⚡ TC-004  OTP expiry resend — HEALED
           Original: .otp-resend-btn (broken)
           Healed:   button:has-text("Resend OTP")
✅ TC-005  Invalid OTP error message

API Results:
✅ POST /investor/login        200 OK  (340ms)
✅ POST /investor/verify-otp  200 OK  (280ms)
✅ POST /verify-otp (expired) 410 as expected

No bugs found. Feature ready for UAT sign-off.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Agent Communication Pattern

```mermaid
graph TD
    subgraph Rule["Golden Rule"]
        R[No agent calls another agent directly\nAll communication goes through Shared State]
    end

    A[agent writes result] --> S[(Shared State)]
    S --> B[orchestrator reads result]
    B --> C[orchestrator decides next agent]
    C --> S
    S --> D[next agent reads what it needs]
```

This means every agent can be tested in isolation, failures are contained, and the full state at any point is inspectable for debugging.

---

*Next: [04_workflow.md](./04_workflow.md) — End-to-end workflow walkthrough*
