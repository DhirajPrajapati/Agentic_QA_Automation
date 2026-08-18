# Phase 3 Master Prompt
## Copy this entire prompt into Claude Chat

---

```
You are helping me build Phase 3 of the QA Orchestrator.
Phases 1 and 2 are complete and passing. Read CLAUDE.md before any code.

## PHASE 3 SCOPE:
Goal: ChromaDB fully operational. Every run writes learnings. Next run
reads them. Self-healing writes healed selectors to memory.

New files: tools/chromadb_client.py, scripts/seed_chromadb.py
Updated files: orchestrator_agent.py, playwright_agent.py, reporter_agent.py

## Task 1: tools/chromadb_client.py

Full implementation with these functions:

SETUP:
- Use chromadb.PersistentClient(path=os.getenv("CHROMADB_PATH","./memory/chromadb"))
- Collection name: "qa_learnings"
- Get or create collection on module import

def query_past_failures(module: str, summary: str, n: int = 5) -> list[str]:
  """
  Query ChromaDB for past learnings relevant to this module and ticket.
  Returns list of document strings (plain text), most relevant first.
  """
  results = collection.query(
      query_texts=[f"{module} {summary}"],
      n_results=n,
      where={"module": module}
  )
  # Return documents list — handle empty results gracefully
  if not results["documents"] or not results["documents"][0]:
      return []
  return results["documents"][0]

def write_learning(doc: str, metadata: dict) -> None:
  """
  Write a learning document to ChromaDB after a test run.
  metadata must include: jira_id, module, run_date.
  """
  from datetime import datetime
  doc_id = f"run_{metadata.get('jira_id','unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
  collection.add(
      documents=[doc],
      metadatas=[{**metadata, "stored_at": datetime.now().isoformat()}],
      ids=[doc_id]
  )
  logger.info("[chromadb] Learning written: %s", doc_id)

def write_healed_selector(
    original: str,
    healed: str,
    module: str,
    element: str
) -> None:
  """
  Write a healed selector to ChromaDB for future runs.
  Confidence starts at 0.85 for first healing.
  """
  from datetime import datetime
  import uuid
  doc = (
      f"Healed selector for {element} in {module}. "
      f"Original: {original}. Working: {healed}. "
      f"Use {healed} in future scripts for this element."
  )
  meta = {
      "module": module,
      "element": element,
      "original_selector": original,
      "healed_selector": healed,
      "confidence": 0.85,
      "healing_date": datetime.now().isoformat(),
      "type": "healed_selector"
  }
  collection.add(
      documents=[doc],
      metadatas=[meta],
      ids=[f"heal_{module.replace('/','_')}_{uuid.uuid4().hex[:8]}"]
  )
  logger.info("[chromadb] Healed selector written: %s → %s", original, healed)

def get_healed_selectors(module: str) -> dict[str, str]:
  """
  Retrieve all previously healed selectors for a module.
  Returns dict: {original_selector: healed_selector}
  """
  results = collection.get(
      where={"$and": [{"module": module}, {"type": "healed_selector"}]}
  )
  healed = {}
  if results["metadatas"]:
      for meta in results["metadatas"]:
          healed[meta["original_selector"]] = meta["healed_selector"]
  return healed

## Task 2: scripts/seed_chromadb.py

Load mock_data/chromadb_seed/known_issues.json.
Format: JSON array of objects with: module, document, confidence, type.

For each issue call write_learning() with metadata:
{
  "module": issue["module"],
  "jira_id": "SEED",
  "run_date": "seed",
  "confidence": issue.get("confidence", 0.75),
  "source": "manual_seed",
  "type": "known_issue"
}

Print after completion:
"Seeded {N} documents to ChromaDB collection: qa_learnings"
"ChromaDB path: {CHROMADB_PATH}"

If called with --reset flag: delete collection and re-create before seeding.

## Task 3: Update agents/orchestrator_agent.py

After fetching Confluence context, add ChromaDB query:

from tools.chromadb_client import query_past_failures

# Build a meaningful query from the Jira summary
module = _resolve_module(state["jira_data"]["fields"]["labels"])
summary = state["jira_data"]["fields"]["summary"]
past = query_past_failures(module, summary, n=5)
state["past_failures"] = past
logger.info("[orchestrator] Retrieved %d past learnings from ChromaDB", len(past))

Add helper function _resolve_module(labels: list[str]) -> str:
- Returns "{user_type}/{module}" eg "investor/login"
- user_type: first of investor/distributor/employee found in labels
- module: first of login/dashboard/redemption/additional-purchase found

## Task 4: Update agents/playwright_agent.py

ADD at the start of playwright_node:
from tools.chromadb_client import get_healed_selectors, write_healed_selector

Before mock execution:
healed_map = get_healed_selectors(module)
Log: f"[playwright] Loaded {len(healed_map)} previously healed selectors"

In mock execution when result is "healed":
- Check if original_selector already in healed_map
- If yes: use existing healed selector (not a new random one)
  Log: "[playwright] Using previously healed selector from memory"
- If no: generate new mock healed selector
  Call write_healed_selector(original, healed, module, tc["flow"])
  Log: "[playwright] New healing written to ChromaDB"

## Task 5: Update agents/reporter_agent.py — add ChromaDB write

After printing results summary, add:

from tools.chromadb_client import write_learning
from datetime import datetime

# Build reflection document
ui_results = state.get("ui_results") or {}
failures = [k for k, v in ui_results.items() if v["status"] == "fail"]
healed = [k for k, v in ui_results.items() if v["status"] == "healed"]

reflection_parts = []
if failures:
    reflection_parts.append(f"Failures: {', '.join(failures)}.")
if healed:
    reflection_parts.append(f"Auto-healed: {', '.join(healed)}.")
for tc_id, result in ui_results.items():
    if result["status"] == "healed":
        reflection_parts.append(
            f"Selector healing in {state['jira_data']['fields']['labels']}: "
            f"TC {tc_id} was healed successfully."
        )
risk = state.get("risk_areas", [])
if risk:
    reflection_parts.append(f"Known risk areas: {'; '.join(risk)}.")

doc = f"Test run for {state['jira_id']}. " + " ".join(reflection_parts)

meta = {
    "jira_id": state["jira_id"],
    "module": _resolve_module(state["jira_data"]["fields"]["labels"]),
    "run_date": datetime.now().isoformat(),
    "total_tests": len(ui_results),
    "failures": len(failures),
    "healed": len(healed),
    "type": "run_reflection"
}

write_learning(doc, meta)
logger.info("[reporter] ChromaDB learning written for %s", state["jira_id"])
print("=== ChromaDB: Learning written ===")

Remove the TODO comment for Phase 3 that was in the stub.

## Validation commands — run all in order:

1. Unit test ChromaDB client:
python -c "
from tools.chromadb_client import write_learning, query_past_failures, write_healed_selector, get_healed_selectors
write_learning('OTP screen slow on UAT — wait 5 seconds before interaction', {'module':'investor/login','jira_id':'TEST-001','run_date':'2025-01-15'})
results = query_past_failures('investor/login', 'OTP not triggering')
assert len(results) >= 1, 'No results returned'
write_healed_selector('.btn-otp-resend', 'button:has-text(\"Resend OTP\")', 'investor/login', 'otp_resend_button')
healed = get_healed_selectors('investor/login')
assert len(healed) >= 1, 'No healed selectors returned'
print('ChromaDB client OK — stored and retrieved')
print('Healed selectors:', healed)
"

2. Seed ChromaDB:
python scripts/seed_chromadb.py
# Expected: "Seeded 3 documents to ChromaDB collection: qa_learnings"

3. First run:
python run.py --jira PROJ-123
# Expected log: "[orchestrator] Retrieved 3 past learnings from ChromaDB"
# Expected at end: "=== ChromaDB: Learning written ==="

4. Second run (must show MORE learnings than first):
python run.py --jira PROJ-123
# Expected log: "[orchestrator] Retrieved N past learnings from ChromaDB" where N > 3
# Expected: healed selectors from run 1 are reused in run 2

5. Verify persistence:
python -c "
from tools.chromadb_client import query_past_failures
r = query_past_failures('investor/login', 'OTP investor login test')
print(f'Total learnings in ChromaDB: {len(r)}')
assert len(r) >= 3
"

## Phase 3 complete when:
- Second run shows more ChromaDB results than first run
- Healing in run 1 is reused in run 2 (no re-healing needed)
- memory/chromadb/ folder exists and has persistent data
- seed_chromadb.py is idempotent (can be run twice without duplicates)
```

