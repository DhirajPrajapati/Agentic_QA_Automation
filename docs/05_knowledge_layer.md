# 05 — Knowledge Layer
## Confluence Knowledge Base Structure

---

## Knowledge Base Structure

```mermaid
graph TD
    KB[PMS Knowledge Base\nConfluence Space]

    KB --> INV[📁 Investor]
    KB --> DIST[📁 Distributor]
    KB --> EMP[📁 Employee]

    INV --> INV1[📄 Login]
    INV --> INV2[📄 Dashboard]
    INV --> INV3[📄 Additional Purchase]
    INV --> INV4[📄 Redemption]
    INV --> INV5[📄 Reports]

    DIST --> DIST1[📄 Login]
    DIST --> DIST2[📄 Commission View]
    DIST --> DIST3[📄 Additional Purchase]
    DIST --> DIST4[📄 Redemption]

    EMP --> EMP1[📄 Login]
    EMP --> EMP2[📄 Admin Panel]
    EMP --> EMP3[📄 User Management]

    style KB fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style INV fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style DIST fill:#E6F1FB,stroke:#185FA5,color:#042C53
    style EMP fill:#FAEEDA,stroke:#854F0B,color:#412402
```

---

## How the Orchestrator Finds the Right Page

```mermaid
flowchart LR
    A[Jira ticket\nLabels: investor, login, otp] --> B[module_map.json]
    B --> C{Match found?}
    C -->|investor + login| D[PAGE_ID_12345\nInvestor Login page]
    C -->|investor + dashboard| E[PAGE_ID_12346\nInvestor Dashboard page]
    C -->|multiple modules| F[Fetch both pages\nmerge context]
    D --> G[Confluence REST API\nGET /wiki/content/12345]
    G --> H[Plain text knowledge\ninjected into shared state]

    style B fill:#FAEEDA,stroke:#854F0B,color:#412402
    style H fill:#EEEDFE,stroke:#534AB7,color:#26215C
```

---

## Page Template — 12 Sections

```mermaid
graph LR
    PAGE[Confluence Page\neg. Investor Login]

    PAGE --> S1[Section 1\nPage Metadata]
    PAGE --> S2[Section 2\nModule Overview]
    PAGE --> S3[Section 3\nUser Roles]
    PAGE --> S4[Section 4\nURLs and Navigation]
    PAGE --> S5[Section 5\nHappy Path Flows]
    PAGE --> S6[Section 6\nEdge Cases + Negatives]
    PAGE --> S7[Section 7\nAPI Endpoints]
    PAGE --> S8[Section 8\nUI Element Hints]
    PAGE --> S9[Section 9\nTest Data]
    PAGE --> S10[Section 10\nPrerequisites]
    PAGE --> S11[Section 11\nKnown Issues]
    PAGE --> S12[Section 12\nChangelog]

    S1 --> A1[orchestrator_agent reads]
    S2 --> A2[analysis_agent reads]
    S3 --> A2
    S4 --> A3[playwright_agent reads]
    S5 --> A4[test_case_agent reads]
    S6 --> A4
    S7 --> A5[api_agent reads]
    S8 --> A6[playwright_agent + self-healing reads]
    S9 --> A7[All execution agents read]
    S10 --> A1
    S11 --> A8[Seeds ChromaDB on first run]
    S12 --> A1

    style PAGE fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style A8 fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

---

## Which Agent Uses Which Section

```mermaid
xychart-beta
    title "Section Usage by Agent"
    x-axis ["S1 Meta", "S2 Overview", "S3 Roles", "S4 URLs", "S5 Flows", "S6 Edge", "S7 APIs", "S8 UI Hints", "S9 Data", "S10 Prereqs", "S11 Known", "S12 Log"]
    y-axis "Agents using this section" 0 --> 5
    bar [2, 2, 2, 2, 3, 3, 2, 3, 4, 1, 2, 1]
```

| Section | Primary agents |
|---|---|
| 1 — Metadata | `orchestrator_agent` (module routing) |
| 2 — Overview | `analysis_agent`, `test_case_agent` |
| 3 — Roles | `analysis_agent`, `test_case_agent` |
| 4 — URLs | `playwright_agent`, `test_script_agent` |
| 5 — Happy paths | `test_case_agent`, `test_script_agent` |
| 6 — Edge cases | `test_case_agent`, `test_script_agent` |
| 7 — APIs | `api_agent`, `test_script_agent` |
| 8 — UI hints | `playwright_agent`, self-healing subgraph |
| 9 — Test data | `playwright_agent`, `api_agent`, `test_script_agent` |
| 10 — Prerequisites | `orchestrator_agent` |
| 11 — Known issues | Seeds ChromaDB, `playwright_agent` |
| 12 — Changelog | `orchestrator_agent` (confidence check) |

---

## Section 8 — UI Element Hints Detail

This is the most critical section for the legacy portal (no `data-testid`).

```mermaid
flowchart TD
    A[Section 8\nUI Element Hints] --> B[playwright_agent\nuses as primary selector reference]
    A --> C[test_script_agent\nuses when writing scripts]
    A --> D[self-healing subgraph\nuses as fallback when selector fails]

    B --> E{Selector works?}
    E -->|Yes| F[Test runs normally]
    E -->|No| G[Self-healing fires\nSection 8 hints provided to LLM]
    G --> H[LLM uses hints to\nsuggest better selectors]
```

**Example Section 8 entry:**
```
Login page elements:
  Email field:    input[name="email"]
  Password field: input[type="password"]
  Login button:   button with text "Login"
                  ⚠️ Changes to "Sign In" after some deployments — try both
  Error toast:    div.error-toast or element containing "Invalid credentials"

OTP page elements:
  OTP input:      input[name="otp"] OR six separate input[type="number"] boxes
                  ⚠️ Layout varies by device — handle both
  Resend button:  button with text "Resend OTP"
                  ⚠️ Class name unreliable — use text selector
  Verify button:  button with text "Verify"
```

---

## Section 11 — Seed Knowledge Flow

```mermaid
flowchart LR
    A[Section 11\nKnown Issues\nwritten by QA team] --> B[seed_chromadb.py\nrun once before first automated run]
    B --> C[(ChromaDB\nqa_learnings collection)]
    C --> D[First automated run\nalready has institutional knowledge]
    D --> E[Subsequent runs\nadd more learnings automatically]
    E --> C

    style A fill:#FAEEDA,stroke:#854F0B,color:#412402
    style C fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style E fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

---

## Maintenance Responsibility Matrix

```mermaid
graph TD
    subgraph Sections["Who updates which sections"]
        DEV[Developer] --> S4[Section 4: URLs]
        DEV --> S7[Section 7: APIs]
        DEV --> S8[Section 8: UI hints]

        QA[QA Engineer] --> S5[Section 5: Happy paths]
        QA --> S6[Section 6: Edge cases]
        QA --> S9[Section 9: Test data]
        QA --> S11[Section 11: Known issues]

        BA[BA / Product] --> S2[Section 2: Overview]
        BA --> S3[Section 3: Roles]
        BA --> S6

        ALL[Everyone] --> S12[Section 12: Changelog]
        ALL --> S10[Section 10: Prerequisites]
    end

    style DEV fill:#E6F1FB,stroke:#185FA5,color:#042C53
    style QA fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style BA fill:#FAEEDA,stroke:#854F0B,color:#412402
    style ALL fill:#EEEDFE,stroke:#534AB7,color:#26215C
```

---

## The Golden Rule

```mermaid
flowchart LR
    A[Jira ticket changes\na user flow] --> B{Same sprint?}
    B -->|Yes ✅| C[Update Confluence page\nin same sprint]
    B -->|No ❌| D[Knowledge goes stale]
    D --> E[Agents generate\nwrong test cases]
    E --> F[False passes\nor missed bugs]
    C --> G[Agents always have\ncurrent knowledge]

    style C fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style D fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style F fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style G fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

---

*Next: [06_self_learning.md](./06_self_learning.md) — How the system learns and improves*
