# 08 — Technology Stack
## Agentic QA Automation System

---

## Full Stack Overview

```mermaid
graph TB
    subgraph Orchestration["🧠 Orchestration"]
        LG[LangGraph 0.2.x\nState machine + routing]
        LC[LangChain 0.3.x\nLLM calls + tools]
        OAI[OpenAI GPT-4o\nIntelligence layer]
    end

    subgraph Testing["🎭 Testing"]
        PW[Playwright 1.45.x\nUI browser automation]
        NW[Newman 6.x\nPostman CLI runner]
    end

    subgraph Memory["🧠 Memory"]
        CDB[ChromaDB 0.5.x\nLocal vector database]
    end

    subgraph Integration["🔌 Integration"]
        JA[Jira REST API v3\nTickets + reporting]
        CA[Confluence REST API v2\nKnowledge base]
        SMTP[SMTP\nEmail reporting]
    end

    subgraph Trigger["🚀 Trigger"]
        GHA[GitHub Actions\nAuto-trigger on PR merge]
        SR[Self-Hosted Runner\nInternal network access]
    end

    subgraph Dev["💻 Development"]
        PY[Python 3.11+\nAll agent code]
        VSC[VS Code\nIDE + Playwright recorder]
        COP[GitHub Copilot\nAI-assisted development]
    end

    LG --> LC --> OAI
    PW --> NW
    GHA --> SR

    style Orchestration fill:#EEEDFE,stroke:#534AB7
    style Testing fill:#FAECE7,stroke:#993C1D
    style Memory fill:#E1F5EE,stroke:#0F6E56
    style Integration fill:#E6F1FB,stroke:#185FA5
    style Trigger fill:#FAEEDA,stroke:#854F0B
    style Dev fill:#F1EFE8,stroke:#5F5E5A
```

---

## LangChain vs LangGraph — Why Both

```mermaid
graph LR
    subgraph LangChain["LangChain — The Ingredients"]
        LC1[LLM calls\nOpenAI wrapper]
        LC2[Prompt templates]
        LC3[ChromaDB retriever]
        LC4[Tool definitions]
        LC5[Output parsers]
    end

    subgraph LangGraph["LangGraph — The Recipe"]
        LG1[Agent state machine]
        LG2[Conditional routing]
        LG3[Retry loops]
        LG4[Parallel execution]
        LG5[Sub-graphs\neg. self-healing]
    end

    LangChain -->|used inside| LangGraph

    style LangChain fill:#E6F1FB,stroke:#185FA5
    style LangGraph fill:#EEEDFE,stroke:#534AB7
```

**Rule of thumb:**
- Linear task (summarise this text) → LangChain alone is fine
- Agent that loops, branches, has state, retries → LangGraph is non-negotiable

This system has loops (self-healing retry), branching (skip API if FE only), state (shared QAState), and parallel execution — LangGraph is the correct choice.

---

## Why Each Tool Was Chosen

```mermaid
graph TD
    subgraph Playwright["Playwright over Selenium"]
        P1[Auto-waiting for elements ✓\nCritical for legacy portal slow loads]
        P2[Built-in screenshot API ✓\nRequired for self-healing]
        P3[VS Code recorder → Python ✓\nDirect format match]
    end

    subgraph Newman["Newman over raw HTTP"]
        N1[Session management ✓\nCookie chains handled natively]
        N2[Pre-request auth scripts ✓\nToken refresh automatic]
        N3[BE team already uses Postman ✓\nZero format conversion]
        N4[JSON report output ✓\nDirect parsing by api_agent]
    end

    subgraph ChromaDB["ChromaDB over cloud vector DB"]
        C1[Local — no cloud account needed ✓\nPhase 1-4 constraint]
        C2[Python native client ✓\nNo server process in dev]
        C3[Server mode for Phase 6 ✓\nSame code, no changes]
        C4[Free — no API costs ✓]
    end

    style Playwright fill:#FAECE7,stroke:#993C1D
    style Newman fill:#E6F1FB,stroke:#185FA5
    style ChromaDB fill:#E1F5EE,stroke:#0F6E56
```

---

## GPT-4o — Why Not a Cheaper Model

```mermaid
flowchart TD
    A{Task type} --> B[Text understanding only\neg. summarisation]
    A --> C[Screenshot analysis\neg. self-healing]
    A --> D[Complex reasoning\neg. test case generation]
    A --> E[Code generation\neg. Playwright scripts]

    B --> F[GPT-3.5 / smaller model ok]
    C --> G[GPT-4o required\nvision capability needed]
    D --> G
    E --> G

    G --> H[Our system uses C, D, E\nGPT-4o is the correct choice]

    style G fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style H fill:#E1F5EE,stroke:#0F6E56,color:#04342C
```

**Cost management:** LLM is only called where reasoning is genuinely needed. Newman execution, ChromaDB writes, and Jira API calls use zero tokens.

---

## What Was Deliberately NOT Chosen

```mermaid
graph LR
    subgraph Rejected["❌ Rejected — Why"]
        R1[Selenium\nNo auto-wait, complex screenshot setup]
        R2[Cypress\nJS only — splits Python stack]
        R3[Pinecone / Weaviate\nCloud — not suitable for local Phase 1]
        R4[SQLite for memory\nNo vector search, no RAG capability]
        R5[LLM fine-tuning\nExpensive, slow, needs labelled data]
        R6[Cloud GitHub runner\nOrg network restrictions]
    end

    style Rejected fill:#FAECE7,stroke:#993C1D
```

---

## Technology Compatibility

```mermaid
graph TD
    subgraph Phase14["Phase 1–4: Local development"]
        W[Windows + VS Code]
        M[macOS]
    end

    subgraph Phase5["Phase 5: GitHub Actions"]
        SR[Self-hosted runner\nDeveloper machine]
    end

    subgraph Phase6["Phase 6: Server"]
        UB[Ubuntu server]
        DK[Docker container]
    end

    W --> SR --> UB
    M --> SR
    UB --> DK

    style Phase14 fill:#E1F5EE,stroke:#0F6E56
    style Phase5 fill:#FAEEDA,stroke:#854F0B
    style Phase6 fill:#EEEDFE,stroke:#534AB7
```

---

## Installation Commands

```bash
# Python dependencies
pip install -r requirements.txt

# Playwright browser
playwright install chromium

# Newman (requires Node.js)
npm install -g newman

# Verify
playwright --version
newman --version
python -c "import langgraph; print('LangGraph OK')"
python -c "import chromadb; print('ChromaDB OK')"
```

---

*Next: [09_phased_delivery.md](./09_phased_delivery.md) — Build phases*
