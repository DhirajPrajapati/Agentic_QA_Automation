# 01 — System Overview
## Agentic QA Automation System

---

## The Problem — Current Manual Process

```mermaid
flowchart TD
    A([PR merged to UAT]) --> B[QA reads Jira ticket manually]
    B --> C[QA writes test cases\n1–2 days]
    C --> D[QA runs manual tests\non portal]
    D --> E{All tests pass?}
    E -- No --> F[QA documents bugs\nin Jira]
    F --> G[Developer fixes bug]
    G --> A
    E -- Yes --> H([UAT sign-off])

    style A fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style H fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style C fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style D fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style F fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
```

**Pain points with this flow:**
- QA testing is a bottleneck — delays every release
- Test cases are inconsistent across QA engineers
- Regression testing is time-consuming and often skipped
- Legacy portal with no `data-testid` attributes makes automation hard
- Knowledge lives in people's heads, not documented systems

---

## The Solution — Agentic QA Pipeline

```mermaid
flowchart TD
    A([PR merged to UAT]) --> B[GitHub Actions fires]
    B --> C[Orchestrator reads\nJira + Confluence + ChromaDB]
    C --> D[Agents generate\ntest cases + scripts]
    D --> E1[Playwright runs\nUI tests]
    D --> E2[Newman runs\nAPI tests]
    E1 --> F{Selector\nfails?}
    F -- Yes --> G[Self-healing fires\nLLM suggests alternatives]
    G --> E1
    F -- No --> H[Results captured]
    E2 --> H
    H --> I[Reporter posts to\nJira + Email]
    I --> J[ChromaDB stores\nlearnings]
    J --> K([Done — same hour])

    style A fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style K fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style G fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style J fill:#EEEDFE,stroke:#534AB7,color:#26215C
```

---

## Before vs After

```mermaid
quadrantChart
    title Manual QA vs Agentic QA
    x-axis Slow --> Fast
    y-axis Inconsistent --> Consistent
    quadrant-1 Ideal
    quadrant-2 Fast but unreliable
    quadrant-3 Avoid
    quadrant-4 Reliable but slow
    Manual QA: [0.15, 0.25]
    Agentic QA: [0.85, 0.90]
```

| Metric | Manual QA | Agentic QA |
|---|---|---|
| Time per ticket | 1–2 days | 4–6 minutes |
| Test consistency | Depends on engineer | Always the same standard |
| Regression coverage | Often skipped | Every run |
| API testing | Rarely done | Every run |
| Self-healing | Manual re-test | Automatic |
| Learning over time | Engineer memory | ChromaDB — persists forever |

---

## User Types Covered

```mermaid
graph LR
    Portal([PMS Portal]) --> Inv[Investor]
    Portal --> Dist[Distributor]
    Portal --> Emp[Employee]

    Inv --> InvL[Login]
    Inv --> InvD[Dashboard]
    Inv --> InvAP[Additional Purchase]
    Inv --> InvR[Redemption]

    Dist --> DistL[Login]
    Dist --> DistC[Commission]
    Dist --> DistAP[Additional Purchase]
    Dist --> DistR[Redemption]

    Emp --> EmpL[Login]
    Emp --> EmpA[Admin Panel]
    Emp --> EmpU[User Management]

    style Portal fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style Inv fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style Dist fill:#E6F1FB,stroke:#185FA5,color:#042C53
    style Emp fill:#FAEEDA,stroke:#854F0B,color:#412402
```

---

## What This System Is NOT

| Not this | Why |
|---|---|
| A no-code tool | Requires an engineer to build and maintain |
| A performance testing tool | Focuses on functional + API correctness |
| A production testing tool | UAT environment only |
| 100% coverage on day one | Coverage grows as recordings and knowledge grow |
| A replacement for developers | Tests code — does not write it |

---

## System Confidence Score

```mermaid
xychart-beta
    title "Design Quality Scores (out of 10)"
    x-axis ["Architecture", "Agent Design", "Knowledge Layer", "Self-Learning", "Overall"]
    y-axis "Score" 0 --> 10
    bar [9, 8.5, 8.5, 8, 9]
```

The 9/10 overall score reflects three key decisions that eliminate common failure modes:
recorded selectors (not hallucinated), BE-provided Postman collections (not invented API structures),
and Confluence as a living knowledge base (not static files that go stale).

---

*Next: [02_architecture.md](./02_architecture.md) — Full system architecture*
