# 04 — End-to-End Workflow
## Agentic QA Automation System

---

## Complete Pipeline — One Diagram

```mermaid
sequenceDiagram
    actor Dev as Developer
    participant GH as GitHub
    participant GA as GitHub Actions
    participant OA as orchestrator_agent
    participant JIRA as Jira API
    participant CONF as Confluence API
    participant CDB as ChromaDB
    participant AA as analysis_agent
    participant TCA as test_case_agent
    participant TSA as test_script_agent
    participant PA as playwright_agent
    participant APIA as api_agent
    participant RA as reporter_agent

    Dev->>GH: Merge PR feature/PROJ-123 → UAT
    GH->>GA: pull_request.closed event
    GA->>GA: Extract PROJ-123 from branch name
    GA->>OA: python run.py --jira PROJ-123

    Note over OA,CDB: Step 1–3: Gather all context
    OA->>JIRA: GET /issue/PROJ-123
    JIRA-->>OA: BRD, labels, acceptance criteria
    OA->>CONF: GET /wiki/content/{page_id}
    CONF-->>OA: Investor Login knowledge page
    OA->>CDB: Query past failures for investor/login
    CDB-->>OA: Healed selectors, known flaky areas

    Note over AA,TCA: Step 4–5: Generate test plan
    OA->>AA: Shared state with all context
    AA-->>OA: Flows to test, risk areas, skip_api=false
    OA->>TCA: Scope + context
    TCA-->>OA: TC-001 through TC-008

    Note over TSA: Step 6: Generate scripts
    OA->>TSA: Test cases + recording path + collection path
    TSA-->>OA: investor_login_test.py + enhanced collection

    Note over PA,APIA: Step 7: Parallel execution
    OA->>PA: Run UI scripts
    OA->>APIA: Run Newman collection

    PA->>PA: TC-001 PASS
    PA->>PA: TC-002 PASS
    PA->>PA: TC-003 PASS
    PA->>PA: TC-004 selector fails → self-heal → HEALED
    PA->>CDB: Write healed selector
    PA->>PA: TC-005 PASS
    PA-->>OA: ui_results complete

    APIA->>APIA: Run newman on collection
    APIA-->>OA: api_results complete

    Note over RA: Step 8: Report + learn
    OA->>RA: All results
    RA->>JIRA: Post comment on PROJ-123
    RA->>RA: Send email to QA team
    RA->>CDB: Write reflection document
    RA-->>Dev: Done in ~5 minutes
```

---

## Step-by-Step Breakdown

### Steps 1–3: Context gathering

```mermaid
flowchart LR
    A[PROJ-123 Jira ticket] --> OA
    B[Confluence: Investor/Login] --> OA
    C[ChromaDB: past 5 runs] --> OA
    OA[orchestrator_agent] --> D[(Shared State\nfull context loaded)]

    A1[BRD text\nAcceptance criteria\nLabels: investor, login, otp] --> A
    B1[12 knowledge sections\nSelectors, flows, APIs\nKnown issues] --> B
    C1[Healed selectors\nFlaky area warnings\nTiming notes] --> C

    style D fill:#EEEDFE,stroke:#534AB7,color:#26215C
```

---

### Step 4: Module resolution

```mermaid
flowchart TD
    A[Jira labels:\ninvestor, login, otp] --> B{module_map.json\nlookup}
    B --> C[investor.login\n→ PAGE_ID_12345]
    C --> D[Confluence fetch:\nInvestor Login page]
    D --> E{Multiple modules?}
    E -->|Yes - login + dashboard| F[Fetch both pages\nmerge context]
    E -->|No - login only| G[Single page context]

    style B fill:#FAEEDA,stroke:#854F0B,color:#412402
```

---

### Steps 5–6: Test generation pipeline

```mermaid
flowchart TD
    A[analysis_agent\nreads full state] --> B[Scope output]
    B --> B1[Flows: login, otp_trigger,\notp_verify, otp_expiry]
    B --> B2[Risk: OTP screen slow,\nbutton label may change]
    B --> B3[skip_api: false]

    B --> C[test_case_agent]
    C --> C1[TC-001: Standard login P1]
    C --> C2[TC-002: OTP on new device P1]
    C --> C3[TC-003: OTP verify P1]
    C --> C4[TC-004: OTP expiry P2]
    C --> C5[TC-005: Invalid OTP P2]
    C --> C6[TC-006 to TC-008: API cases]

    C --> D[test_script_agent]
    D --> E[Load recording\ninvestor/login_happy_path.py]
    D --> F[Load BE collection\ninvestor/login.json]
    E --> G[investor_login_test.py\nwith assertions + negatives]
    F --> H[Enhanced collection\nwith negative cases]
```

---

### Step 7: Execution — self-healing detail

```mermaid
flowchart TD
    A[TC-004: OTP expiry\nclick Resend OTP button] --> B[Playwright runs]
    B --> C{.otp-resend-btn\nfound?}
    C -->|Yes| D[TC-004 PASS]
    C -->|No| E[SELF-HEAL: Screenshot taken]
    E --> F[LLM receives screenshot\n+ failed selector\n+ test intent]
    F --> G[Alternative 1:\nbutton:has-text Resend OTP]
    G --> H{Found?}
    H -->|Yes| I[TC-004 HEALED ⚡]
    I --> J[Write to ChromaDB:\n.otp-resend-btn\n→ button:has-text Resend OTP]
    H -->|No| K[Alternative 2:\n.otp-actions > button:last-child]
    K --> L{Found?}
    L -->|Yes| I
    L -->|No| M[Alternative 3:\n positional selector]
    M --> N{Found?}
    N -->|Yes| I
    N -->|No| O[TC-004 FAIL 🔴\nscreenshot + log]

    style E fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style I fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style J fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style O fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
```

---

### Step 8: Results and learning

```mermaid
flowchart LR
    UI[ui_results\n5 tests: 4 pass, 1 healed] --> RA[reporter_agent]
    API[api_results\n3 requests: all pass] --> RA

    RA --> J[Jira comment\nstructured report]
    RA --> E[Email\nQA team notification]
    RA --> C[ChromaDB write\nreflection document]

    C --> C1[What failed: TC-004\nOTP resend selector]
    C --> C2[Healed selector:\nbutton:has-text Resend OTP]
    C --> C3[Deployment change:\nbutton class removed]
    C --> C4[Recommendation:\nUpdate Confluence Section 8]

    style RA fill:#FAEEDA,stroke:#854F0B,color:#412402
    style C fill:#EEEDFE,stroke:#534AB7,color:#26215C
```

---

## Timing Breakdown

```mermaid
gantt
    title Single Run Timeline (~5 minutes total)
    dateFormat mm:ss
    axisFormat %M:%S

    section Setup
    Trigger + config load        :00:00, 5s
    Jira + Confluence fetch      :00:05, 10s
    ChromaDB RAG query           :00:15, 3s

    section Generation
    Analysis agent               :00:18, 15s
    Test case agent              :00:33, 20s
    Script generation            :00:53, 30s

    section Execution
    Playwright UI tests          :01:23, 120s
    Newman API tests             :01:23, 45s

    section Reporting
    Report compilation           :03:23, 10s
    Jira post + email            :03:33, 15s
    ChromaDB write               :03:48, 10s
```

---

## Orchestrator Decision Tree

```mermaid
flowchart TD
    A[Jira ticket received] --> B{Labels include\nFE module?}
    B -->|Yes| C{Labels include\nBE module?}
    B -->|No| D[BE-only ticket\nAPI tests only]
    C -->|Yes| E[Full pipeline\nUI + API]
    C -->|No| F[FE-only ticket\nUI tests only\nskip_api = true]

    E --> G{Recording\nexists?}
    G -->|Yes| H[Use recording\nas UI baseline]
    G -->|No| I[LLM generates\nfrom Confluence hints]

    E --> J{Postman collection\nexists?}
    J -->|Yes| K[Use BE collection\nas API baseline]
    J -->|No| L[LLM generates\nAPI requests]

    style E fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style F fill:#FAEEDA,stroke:#854F0B,color:#412402
    style D fill:#E6F1FB,stroke:#185FA5,color:#042C53
```

---

*Next: [05_knowledge_layer.md](./05_knowledge_layer.md) — Confluence knowledge base structure*
