# 06 — Self-Learning System
## ChromaDB Memory and Continuous Improvement

---

## The Learning Loop

```mermaid
flowchart TD
    A([New test run starts]) --> B[Orchestrator queries ChromaDB\nRAG similarity search]
    B --> C{Past learnings\nexist for this module?}
    C -->|No — first run| D[Rely on Confluence\nSection 11 seed data]
    C -->|Yes| E[Inject past context\ninto shared state]
    E --> F[Agents use learnings\nto make smarter decisions]
    D --> F
    F --> G[Tests execute]
    G --> H[Self-healing fires\nif selector fails]
    H --> I[Healed selector written\nto ChromaDB immediately]
    G --> J[reporter_agent compiles results]
    J --> K[Reflection document\nwritten to ChromaDB]
    K --> L([Next run is smarter])
    L --> A

    style E fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style I fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style K fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style L fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

---

## Three Levels of Learning

```mermaid
graph TD
    subgraph L1["Level 1 — Reflection Node"]
        R[After every run\nLLM summarises what failed and why]
    end

    subgraph L2["Level 2 — ChromaDB Write"]
        W[Persistent vector storage\nFailures, healed selectors, flaky patterns]
    end

    subgraph L3["Level 3 — RAG Query"]
        Q[Before every run\nRetrieve relevant past context]
    end

    L1 --> L2 --> L3 --> L1

    style L1 fill:#E6F1FB,stroke:#185FA5,color:#042C53
    style L2 fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style L3 fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

---

## ChromaDB Document Structure

```mermaid
classDiagram
    class ChromaDBDocument {
        +String document
        +String jira_id
        +String module
        +String user_type
        +String run_date
        +String outcome
        +List failures
        +Dict healed_selectors
        +List timing_warnings
        +List flaky_areas
        +Float confidence
    }

    class HealedSelector {
        +String original
        +String healed
        +String element_description
        +String healing_date
        +Float confidence
    }

    class ReflectionDoc {
        +String run_summary
        +List failures
        +List timing_issues
        +List deployment_changes
        +List recommendations
    }

    ChromaDBDocument --> HealedSelector
    ChromaDBDocument --> ReflectionDoc
```

---

## Self-Healing Deep Dive

```mermaid
sequenceDiagram
    participant PW as Playwright
    participant SH as Self-Healing Subgraph
    participant LLM as OpenAI GPT-4o
    participant CDB as ChromaDB

    PW->>PW: selector ".otp-resend-btn" not found
    PW->>SH: trigger self-healing
    SH->>PW: take screenshot of current DOM
    PW-->>SH: screenshot.png

    SH->>CDB: query: "otp resend button investor login"
    CDB-->>SH: past healing: button:has-text('Resend OTP') confidence:0.85

    SH->>LLM: screenshot + failed selector +\ntest intent + past healing hint
    LLM-->>SH: alternatives ranked:\n1. button:has-text('Resend OTP')\n2. .otp-actions > button:last-child\n3. [data-action="resend-otp"]

    SH->>PW: try alternative 1
    PW->>PW: button:has-text('Resend OTP') found ✓
    PW-->>SH: element located

    SH->>CDB: write healed selector\noriginal → healed, confidence: 0.95
    CDB-->>SH: stored ✓

    SH-->>PW: continue test with healed selector
    PW->>PW: TC-004 HEALED ⚡
```

---

## Confidence Score System

```mermaid
graph TD
    A[Learning written\nto ChromaDB] --> B[Initial confidence set]

    B --> C{Source?}
    C -->|Healed selector\nconfirmed twice| D[0.95 — Very high]
    C -->|Single confirmed healing| E[0.85 — High]
    C -->|Past failure, no fix yet| F[0.70 — Medium]
    C -->|Manual seed from Confluence| G[0.75 — Medium]

    D --> H{Time and events\nreduce confidence}
    E --> H
    F --> H
    G --> H

    H -->|Confluence page updated\nafter this learning| I[Reduce to 0.50]
    H -->|Same element fails again| J[Reduce to 0.40]
    H -->|Older than 30 days, unconfirmed| K[Reduce to 0.30]

    I --> L[Orchestrator treats\nwith lower trust]
    J --> L
    K --> L

    style D fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style E fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style I fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style J fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style K fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
```

---

## System Intelligence Over Time

```mermaid
xychart-beta
    title "Self-Healing Events Per Run (decreases as ChromaDB grows)"
    x-axis ["Run 1", "Run 3", "Run 5", "Run 10", "Run 20", "Run 30+"]
    y-axis "Healing events" 0 --> 10
    line [8, 6, 4, 2, 1, 0]
```

```mermaid
xychart-beta
    title "Test Pass Rate Per Run (increases as ChromaDB grows)"
    x-axis ["Run 1", "Run 3", "Run 5", "Run 10", "Run 20", "Run 30+"]
    y-axis "Pass rate %" 0 --> 100
    line [60, 72, 82, 90, 96, 99]
```

---

## RAG Query — What the Orchestrator Asks

```mermaid
flowchart LR
    A[Module: investor/login\nJira summary: OTP not triggering] --> B[ChromaDB query]
    B --> C[Semantic similarity search\nn=5 most relevant results]
    C --> D[Result 1: OTP screen slow 4-5s\nconfidence: 0.85]
    C --> E[Result 2: Login button → Sign In\nconfidence: 0.90]
    C --> F[Result 3: Healed OTP resend selector\nconfidence: 0.95]
    C --> G[Result 4: OTP input layout varies\nconfidence: 0.80]
    D & E & F & G --> H[Injected into shared state\nas past_failures]
    H --> I[test_script_agent uses:\nhealed selectors directly]
    H --> J[playwright_agent uses:\n5s explicit wait before OTP screen]

    style B fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style H fill:#EEEDFE,stroke:#534AB7,color:#26215C
```

---

## Seeding ChromaDB — Before First Run

```mermaid
flowchart TD
    A[Confluence\nSection 11: Known Issues] --> B[scripts/seed_chromadb.py\nrun once manually]
    B --> C[(ChromaDB\nqa_learnings)]
    C --> D[Run 1 already knows:\nOTP is slow, button labels change,\nOTP input may be 6 boxes]
    D --> E[First run much more\nstable than without seeding]

    style B fill:#E6F1FB,stroke:#185FA5,color:#042C53
    style C fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style E fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

---

## What Gets Written After Every Run

```mermaid
graph TD
    RA[reporter_agent] --> CDB[(ChromaDB)]

    CDB --> DOC[Reflection Document]
    DOC --> F1[What failed and why]
    DOC --> F2[Healed selectors\noriginal → working]
    DOC --> F3[Timing issues detected\neg. OTP 4.8s load]
    DOC --> F4[Deployment changes spotted\neg. button label changed]
    DOC --> F5[Recommendations\neg. update Confluence Section 8]

    style RA fill:#FAEEDA,stroke:#854F0B,color:#412402
    style CDB fill:#EEEDFE,stroke:#534AB7,color:#26215C
```

---

*Next: [07_folder_structure.md](./07_folder_structure.md) — Project folder layout*
