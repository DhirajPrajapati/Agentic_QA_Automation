# 10 — Team Conventions
## Agentic QA Automation System

---

## Why These Conventions Matter

```mermaid
graph TD
    A[Jira label missing or wrong] --> B[Orchestrator cannot find\nConfluence page]
    B --> C[Wrong knowledge loaded]
    C --> D[Wrong test cases generated]
    D --> E[Tests run against wrong flows]

    F[Branch name wrong] --> G[GitHub Actions\ncannot extract Jira ID]
    G --> H[Auto-trigger fails\nsilently]

    I[Confluence not updated\nafter flow change] --> J[Agents use stale knowledge]
    J --> K[False passes\nor missed bugs]

    style A fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style F fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style I fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style E fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style H fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
    style K fill:#FAECE7,stroke:#993C1D,color:#4A1B0C
```

These conventions are not suggestions. If they are not followed, the system cannot function correctly.

---

## 1. Jira Label Taxonomy

```mermaid
graph TD
    TICKET[Every Jira ticket\nthat QA will test] --> UT[User type label\nPick exactly ONE]
    TICKET --> ML[Module labels\nPick ALL that apply]

    UT --> U1[investor]
    UT --> U2[distributor]
    UT --> U3[employee]

    ML --> M1[login]
    ML --> M2[dashboard]
    ML --> M3[additional-purchase]
    ML --> M4[redemption]
    ML --> M5[reports]
    ML --> M6[commission]
    ML --> M7[admin-panel]
    ML --> M8[user-management]

    style UT fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style ML fill:#E6F1FB,stroke:#185FA5,color:#042C53
```

**Label rules:**
- Lowercase only — `investor` not `Investor`
- Hyphens for spaces — `admin-panel` not `admin panel`
- Every ticket needs at minimum 1 user type + 1 module label
- Tickets with no matching labels are silently skipped by the orchestrator

**Examples:**

```mermaid
graph LR
    T1[Fix OTP not triggering\nfor investor login] --> L1[investor + login + otp]
    T2[Redemption form broken\nfor distributor] --> L2[distributor + redemption]
    T3[Employee admin panel\nuser deactivation] --> L3[employee + admin-panel + user-management]
    T4[Dashboard loads slow\nfor all investors] --> L4[investor + dashboard]
```

---

## 2. Branch Naming Convention

```mermaid
graph TD
    FORMAT["Required format:\n{type}/{JIRA-ID}-{description}"]

    FORMAT --> T[Branch types]
    T --> BF[feature/]
    T --> BB[bugfix/]
    T --> BH[hotfix/]
    T --> BC[chore/ ← skips QA trigger]

    FORMAT --> EXAMPLE[Examples]
    EXAMPLE --> E1[feature/PROJ-123-investor-otp-fix]
    EXAMPLE --> E2[bugfix/PROJ-456-redemption-validation]
    EXAMPLE --> E3[hotfix/PROJ-789-login-crash]

    FORMAT --> RULES[Rules]
    RULES --> R1[Jira ID format: LETTERS-NUMBERS\neg. PROJ-123]
    RULES --> R2[Jira ID immediately after type/]
    RULES --> R3[No spaces anywhere]
    RULES --> R4[chore/ branches skip auto-trigger]

    style FORMAT fill:#EEEDFE,stroke:#534AB7,color:#26215C
    style EXAMPLE fill:#E1F5EE,stroke:#0F6E56
```

**How GitHub Actions extracts the Jira ID:**
```bash
BRANCH="feature/PROJ-123-investor-otp-fix"
JIRA_ID=$(echo "$BRANCH" | grep -oP '[A-Z]+-[0-9]+')
# Result: PROJ-123
```

If the branch name does not contain a valid Jira ID, the workflow exits with a clear error and posts a comment on the PR.

---

## 3. Confluence Maintenance Rules

```mermaid
flowchart TD
    A[Developer merges ticket\nthat changes a flow] --> B{Does this change\naffect a flow?}
    B -->|Yes| C[Update Confluence\nin same sprint]
    B -->|No — refactor only| D[No Confluence update needed]

    C --> E{What changed?}
    E -->|Happy path steps| F[Update Section 5\nReference new recording if re-recorded]
    E -->|Error messages| G[Update Section 6\nExact copy-paste from UI]
    E -->|API endpoints| H[Update Section 7\nNew signature, error codes]
    E -->|UI elements| I[Update Section 8\nNew selectors, label changes]
    E -->|Any change| J[ALWAYS add row\nto Section 12 Changelog]

    style C fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style J fill:#FAEEDA,stroke:#854F0B,color:#412402
```

**Responsibility matrix:**

| Section | Developer | QA Engineer | BA / Product |
|---|---|---|---|
| 2 — Overview | | | ✅ |
| 3 — Roles | | | ✅ |
| 4 — URLs | ✅ | | |
| 5 — Happy paths | | ✅ | |
| 6 — Edge cases | | ✅ | ✅ |
| 7 — APIs | ✅ | | |
| 8 — UI hints | ✅ | ✅ | |
| 9 — Test data | | ✅ | |
| 10 — Prerequisites | ✅ | | |
| 11 — Known issues | | ✅ | |
| 12 — Changelog | ✅ | ✅ | ✅ |

---

## 4. Recording Conventions

```mermaid
flowchart TD
    A{When to re-record?} --> B[New module added\nto system]
    A --> C[Flow changed significantly\nold recording invalid]
    A --> D[Self-healing modified\ntoo many selectors]

    B --> E[Record on UAT\nnot local, not production]
    C --> E
    D --> E

    E --> F[Use VS Code\nPlaywright extension]
    F --> G[Use designated\nUAT test account\nConfluence Section 9]
    G --> H[Clean flow only\nno accidental clicks]
    H --> I[Save as Python .py\nnot JSON or TypeScript]
    I --> J[Replace existing file\nrecordings/user_type/module_happy_path.py]
    J --> K[Update Confluence Section 5\nReference new recording + date]

    style E fill:#E1F5EE,stroke:#0F6E56,color:#04342C
    style J fill:#FAEEDA,stroke:#854F0B,color:#412402
```

---

## 5. BE Team Postman Collection Rules

```mermaid
flowchart LR
    A[New API endpoint\nor changed endpoint] --> B[BE developer updates\nPostman collection]
    B --> C[Export updated .json file]
    C --> D[Replace file in\npostman_collections/user_type/module.json]
    D --> E[Commit in SAME PR\nas API code change]

    style E fill:#FAEEDA,stroke:#854F0B,color:#412402
```

**Checklist for each Postman collection:**
- [ ] All endpoints for the module included (not just happy path)
- [ ] Pre-request script for authentication (token fetch)
- [ ] At least one test assertion per request (status code minimum)
- [ ] UAT environment file provided with `{{base_url}}` and `{{auth_token}}`
- [ ] Variables used consistently — no hardcoded UAT URLs in requests

---

## Quick Reference Card

```mermaid
graph TD
    subgraph JL["Jira Labels"]
        JL1[investor / distributor / employee\n+\nlogin / dashboard / redemption / ...]
    end

    subgraph BN["Branch Naming"]
        BN1[feature/PROJ-123-description\nbugfix/PROJ-456-description]
    end

    subgraph CF["Confluence"]
        CF1[Update same sprint\nAlways update Section 12\nError messages exact copy-paste]
    end

    subgraph PC["Postman Collections"]
        PC1[Update in same PR\nInclude auth script\nUAT environment file]
    end

    subgraph RC["Recordings"]
        RC1[Record on UAT only\nSave as .py\nClean flows only]
    end

    style JL fill:#E1F5EE,stroke:#0F6E56
    style BN fill:#E6F1FB,stroke:#185FA5
    style CF fill:#FAEEDA,stroke:#854F0B
    style PC fill:#EEEDFE,stroke:#534AB7
    style RC fill:#FAECE7,stroke:#993C1D
```

---

## Convention Compliance Checklist — Before Merging Any PR

```
PR Checklist for QA Orchestrator Compatibility

[ ] Jira ticket has at least one user type label (investor / distributor / employee)
[ ] Jira ticket has at least one module label (login / redemption / etc.)
[ ] Branch name follows format: {type}/{JIRA-ID}-{description}
[ ] If flow changed → Confluence page updated in this sprint
[ ] If Confluence updated → Section 12 Changelog has new row
[ ] If API changed → Postman collection updated and committed in this PR
[ ] If happy path changed → New recording made and committed
[ ] No production credentials anywhere in the codebase
[ ] .env not committed (check .gitignore)
```

---

*This completes the QA Orchestrator documentation set.*

*Contact: Dhiraj Prajapati — TechStalwarts Software Development LLP*
