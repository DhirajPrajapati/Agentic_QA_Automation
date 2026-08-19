"""
test_case_agent — Generates professional autonomous QA test cases per flow.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes

Fully autonomous — no human approval gate. Format follows the
copilot-instructions.md column structure (module, sub-module, preconditions,
numbered steps, expected results, automation_status, ...).
"""
import json
import logging

from graph.state import QAState
from tools.llm_client import invoke_with_retry

logger = logging.getLogger(__name__)

TEST_CASE_PROMPT = """You are a senior QA engineer generating professional
test cases for a Portfolio Management System (PMS) portal.
You are part of a fully autonomous QA pipeline — no human review needed.

Jira Ticket ID: {jira_id}
Jira Summary: {summary}
Jira Priority: {priority}
Acceptance Criteria: {criteria}

Confluence Module Knowledge:
{confluence_context}

Flow to test: {flow}
Risk Areas from memory: {risk_areas}
Test case numbering starts at: {start_index}

Generate test cases in this EXACT JSON format.
Output ONLY a valid JSON array. No markdown, no explanation,
no code fences. Raw JSON array only.

[
  {{
    "jira_id": "{jira_id}",
    "test_case_id": "ModuleName_{start_index:03d}",
    "module": "ModuleName from Confluence",
    "sub_module": "Sub-feature or strategy type",
    "priority": "HIGH or MEDIUM or LOW",
    "type": "Smoke or Functional or Regression",
    "test_case_description": "One clear sentence of what is validated",
    "preconditions": [
      "1. First required system/user state before test",
      "2. Second precondition",
      "3. Third precondition"
    ],
    "test_steps": [
      "1) First action the tester performs",
      "2) Second action",
      "3) Third action",
      "4) Fourth action",
      "5) Fifth action",
      "6) Sixth action"
    ],
    "expected_results": [
      "1) First expected outcome",
      "2) Second expected outcome",
      "3) Third expected outcome"
    ],
    "postconditions": "System state after successful completion",
    "tags": "@smoke",
    "automation_status": "Auto-Generated",
    "remarks": "Generated autonomously by QA Orchestrator. Jira: {jira_id}. Source: Confluence knowledge base.",
    "scenario_nature": "Positive",
    "negative_category": "NA"
  }}
]

STRICT RULES:

test_case_id:
  Extract module from Confluence feature name, CamelCase, no spaces.
  Number sequentially from {start_index}, padded to 3 digits.
  Example: AdditionalPurchase_001, AdditionalPurchase_002

module:
  From Confluence module name or Jira summary feature name.
  CamelCase. Example: AdditionalPurchase, InvestorLogin

sub_module:
  From Confluence sub-feature or strategy type.
  Example: "Existing Strategy - Investor Portal"

priority:
  Critical/Blocker → HIGH
  Major/High → HIGH
  Minor/Medium → MEDIUM
  Trivial/Low → LOW

type:
  First happy path test → Smoke
  Additional positive tests → Functional
  Negative and edge cases → Regression

preconditions:
  Numbered list. Extract from Confluence prerequisites and user roles.
  Minimum 3. Write as complete sentences.
  Be specific to this module and flow.

test_steps:
  Numbered with ) format: "1) action"
  Extract from Confluence happy path flows.
  Minimum 6 steps. Include navigation, data entry, clicks, verifications.
  Steps must be detailed enough for a new QA engineer to follow.

expected_results:
  Numbered with ) format: "1) outcome"
  Extract from acceptance criteria and Confluence business rules.
  Minimum 3. Be specific with values where possible.

postconditions:
  What is true in system after test passes.

tags:
  Smoke → @smoke
  Functional → @functional
  Regression → @regression

automation_status:
  Always "Auto-Generated" — this system is fully autonomous.
  No human approval gate exists.

remarks:
  Always include Jira ticket reference and scope notes.
  Note any intentional exclusions.

scenario_nature:
  Happy path → Positive
  Error/validation → Negative

negative_category:
  Positive scenarios → NA
  Negative scenarios → one of:
  Validation | Auth | Business Rule | API Error | Boundary | Other

GENERATE FOR FLOW "{flow}":
1. One Smoke test — happy path, Positive, all steps detailed
2. One Functional test — additional positive validation
3. One Regression test — negative/error scenario, Negative
4. One Regression test — boundary condition

Minimum 4 test cases. Make test steps detailed and specific.
"""

_MODULE_INDICATORS: list[tuple[str, str]] = [
    ("Additional Purchase", "AdditionalPurchase"),
    ("AdditionalPurchase", "AdditionalPurchase"),
    ("Redemption", "Redemption"),
    ("Investor Login", "InvestorLogin"),
    ("Login", "InvestorLogin"),
    ("Dashboard", "Dashboard"),
    ("SIP", "SIP"),
    ("Switch", "Switch"),
    ("Portfolio", "Portfolio"),
]


def _extract_module_name(confluence_context: str, jira_summary: str) -> str:
    """Extract a clean CamelCase module name from Confluence text or Jira summary."""
    for keyword, module_name in _MODULE_INDICATORS:
        if keyword.lower() in confluence_context.lower():
            return module_name
        if keyword.lower() in jira_summary.lower():
            return module_name
    words = jira_summary.split()
    return "".join(w.capitalize() for w in words[:2]) if words else "Module"


def _build_prompt(
    jira_id: str,
    summary: str,
    priority: str,
    criteria: str,
    confluence_context: str,
    flow: str,
    risk_areas: str,
    start_index: int,
) -> list[dict[str, str]]:
    """Build the per-flow test case prompt as a plain LLM message list."""
    content = TEST_CASE_PROMPT.format(
        jira_id=jira_id,
        summary=summary,
        priority=priority,
        criteria=criteria[:800],
        confluence_context=confluence_context[:4000],
        flow=flow,
        risk_areas=risk_areas,
        start_index=start_index,
    )
    return [{"role": "user", "content": content}]


def test_case_node(state: QAState) -> QAState:
    """
    Generate professional autonomous QA test cases for every flow in
    state["flows_to_test"]. Fully autonomous — no human approval gate.

    Reads:  jira_data, confluence_context, flows_to_test, risk_areas
    Writes: test_cases, status, current_phase
    """
    logger.info(
        "[test_case] Generating professional test cases for %d flows...",
        len(state["flows_to_test"]),
    )

    fields = state["jira_data"].get("fields", {})
    summary = fields.get("summary", "")
    criteria = fields.get("acceptance_criteria", "")
    if isinstance(criteria, dict):
        criteria = " ".join(str(v) for v in criteria.values())
    elif isinstance(criteria, list):
        criteria = " ".join(str(v) for v in criteria)

    priority = fields.get("priority", {})
    if isinstance(priority, dict):
        priority = priority.get("name", "Medium")

    risk_str = "; ".join(state["risk_areas"]) if state["risk_areas"] else "None"
    jira_id = state["jira_id"]
    context = state["confluence_context"]
    module_name = _extract_module_name(context, summary)

    all_cases: list[dict] = []
    tc_counter = 1

    for flow in state["flows_to_test"]:
        logger.info("[test_case] Generating cases for flow: %s", flow)
        raw = ""
        try:
            messages = _build_prompt(
                jira_id=jira_id,
                summary=summary,
                priority=priority,
                criteria=criteria,
                confluence_context=context,
                flow=flow,
                risk_areas=risk_str,
                start_index=tc_counter,
            )
            raw = invoke_with_retry(messages=messages, agent_type="test_case")

            clean = raw.strip()
            for fence in ["```json", "```JSON", "```"]:
                if clean.startswith(fence):
                    clean = clean[len(fence):]
                    break
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            cases = json.loads(clean)
            if not isinstance(cases, list):
                cases = [cases]

            for case in cases:
                case["test_case_id"] = f"{module_name}_{tc_counter:03d}"
                case["jira_id"] = jira_id
                case["automation_status"] = "Auto-Generated"
                case["remarks"] = (
                    case.get("remarks", "")
                    + f" | Jira: {jira_id} | Auto-generated by QA Orchestrator."
                )
                tc_counter += 1

            all_cases.extend(cases)
            logger.info("[test_case] Flow '%s': %d cases", flow, len(cases))

        except json.JSONDecodeError as e:
            logger.error("[test_case] JSON parse failed for '%s': %s", flow, str(e))
            logger.error("[test_case] Raw (first 400 chars): %s", raw[:400])
            state["errors"].append({
                "agent": "test_case",
                "flow": flow,
                "error": f"JSON parse error: {str(e)}",
            })
        except Exception as e:
            logger.error("[test_case] Failed for '%s': %s", flow, str(e))
            state["errors"].append({
                "agent": "test_case",
                "flow": flow,
                "error": str(e),
            })

    state["test_cases"] = all_cases

    smoke = sum(1 for c in all_cases if c.get("type") == "Smoke")
    functional = sum(1 for c in all_cases if c.get("type") == "Functional")
    regression = sum(1 for c in all_cases if c.get("type") == "Regression")
    positive = sum(1 for c in all_cases if c.get("scenario_nature") == "Positive")
    negative = sum(1 for c in all_cases if c.get("scenario_nature") == "Negative")

    logger.info(
        "[test_case] Total: %d | Smoke:%d Functional:%d Regression:%d"
        " | Positive:%d Negative:%d",
        len(all_cases), smoke, functional, regression, positive, negative,
    )

    if not all_cases:
        logger.warning("[test_case] No test cases generated — check LLM response")

    state["status"] = "test_cases_complete"
    state["current_phase"] = "test_script"

    # === Attach test cases to Jira ticket immediately ===
    # QA team can review cases while pipeline continues running
    try:
        from pathlib import Path
        from tools.jira_client import (
            attach_file_to_ticket,
            format_test_cases_as_text,
        )

        tc_text = format_test_cases_as_text(
            test_cases=state["test_cases"],
            jira_id=state["jira_id"],
            jira_summary=summary,
        )

        # Save formatted file locally
        tc_file_name = f"{state['jira_id']}_test_cases.md"
        tc_file_path = Path(f"outputs/reports/{tc_file_name}")
        tc_file_path.parent.mkdir(parents=True, exist_ok=True)
        tc_file_path.write_text(tc_text)
        logger.info("[test_case] Test cases saved: %s", tc_file_path)

        # Attach to Jira immediately
        attached = attach_file_to_ticket(
            jira_id=state["jira_id"],
            file_path=str(tc_file_path),
            file_name=tc_file_name,
        )

        if attached:
            state["tc_attachment_name"] = tc_file_name
            logger.info(
                "[test_case] Test cases attached to Jira: %s — "
                "QA team can review while pipeline runs",
                tc_file_name,
            )
        else:
            state["tc_attachment_name"] = None
            logger.warning("[test_case] Attachment failed — continuing pipeline")

    except Exception as e:
        logger.error("[test_case] Attachment error: %s", str(e))
        state["errors"].append({
            "agent": "test_case",
            "error": f"TC attachment: {str(e)}",
        })
        state["tc_attachment_name"] = None

    return state
