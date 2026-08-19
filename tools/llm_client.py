"""
llm_client — Wrapper for Azure OpenAI / OpenAI / org-gateway LLM calls with
mock support and retry logic. Provider selected via LLM_PROVIDER
(azure|openai|org_gateway).
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import json
import logging
import os
import time
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

USE_MOCK_LLM: bool = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "azure").lower()
ORG_LLM_ENDPOINT: str = os.getenv("ORG_LLM_ENDPOINT", "")

api_key = os.getenv("OPENAI_API_KEY", "")
if not api_key or api_key == "placeholder_add_org_key_later":
    logger.warning("[llm_client] No real OpenAI key set. LLM calls will fail.")

# LLM_PROVIDER selects the real (non-mock) backend: "azure" (org default) or
# "openai" (fallback). Only consulted by _build_llm() when USE_MOCK_LLM=false.
_azure_key = os.getenv("AZURE_OPENAI_API_KEY", "")
if os.getenv("LLM_PROVIDER", "azure").lower() == "azure" and (
    not _azure_key or _azure_key == "placeholder_add_org_key_later"
):
    logger.warning("[llm_client] No real Azure OpenAI key set. LLM calls will fail.")

# One hardcoded, realistic mock response per agent type — lets Phase 1-4
# agents be built and run end-to-end before the org OpenAI key arrives.
# Keyed by the agent_type each agent passes to invoke_with_retry(). Every
# entry is valid JSON except test_script_ui, whose real LLM output is a
# complete .py file rather than JSON.
_MOCK_RESPONSES: dict[str, str] = {
    "analysis": json.dumps(
        {
            "flows_to_test": [
                "standard_login",
                "otp_trigger",
                "otp_verify",
                "otp_expiry",
            ],
            "skip_api": False,
            "risk_areas": [
                "OTP screen takes 4-5s to load on UAT",
                "Login button label changes after first click",
            ],
            "user_types_in_scope": ["retail_investor", "institutional_investor"],
        }
    ),
    # Professional autonomous format (test_case_agent) — no human approval
    # gate, columns match copilot-instructions.md Section 6.2. Real values
    # are overwritten by test_case_agent (test_case_id, jira_id, remarks) —
    # this mock only needs to be valid JSON matching the schema.
    "test_case": json.dumps(
        [
            {
                "jira_id": "PROJ-123",
                "test_case_id": "AdditionalPurchase_001",
                "module": "AdditionalPurchase",
                "sub_module": "Existing Strategy - Investor Portal",
                "priority": "HIGH",
                "type": "Smoke",
                "test_case_description": "Validate successful Additional Purchase for existing strategy when PAN-holder AUM rule is satisfied and investor completes online payment flow",
                "preconditions": [
                    "1. Investor has active portal access with valid PAN, password, and OTP channel",
                    "2. Selected PAN-holder combination has active existing DI code(s)",
                    "3. PAN-holder-combination AUM satisfies existing-strategy threshold (50 Lakh minimum)",
                    "4. Purchase amount valid: minimum 5 Lakhs in multiples of 1 Thousand",
                    "5. Net Banking path is enabled in UAT environment",
                ],
                "test_steps": [
                    "1) Open portal and log in as Investor using PAN, password, and OTP",
                    "2) Navigate to Transactions module and click Additional Purchase",
                    "3) Select holding pattern and PAN-holder combination from dropdown",
                    "4) Verify only active existing DI codes are listed and select one",
                    "5) Enter valid amount for existing strategy (example: 5,00,000)",
                    "6) Click Purchase and select Relationship Manager if prompted",
                    "7) Choose Net Banking as payment mode and accept Terms and Conditions",
                    "8) Proceed to payment, complete OTP confirmation, complete payment",
                    "9) Verify success confirmation and return to dashboard",
                ],
                "expected_results": [
                    "1) Existing DI codes for selected PAN-holder combination displayed correctly",
                    "2) Entered amount passes existing-strategy validations (>= 5 Lakhs, multiple of 1 Thousand)",
                    "3) Transaction submitted successfully after OTP and payment success",
                    "4) Success confirmation shown with transaction reference number",
                    "5) Transaction visible in recent transactions on dashboard",
                ],
                "postconditions": "Additional Purchase request created with success status. Transaction reference available in portal flow and recent transactions.",
                "tags": "@smoke",
                "automation_status": "Auto-Generated",
                "remarks": "Scope restricted to Existing Strategy only. New Strategy excluded. Generated autonomously by QA Orchestrator. Jira: PROJ-123.",
                "scenario_nature": "Positive",
                "negative_category": "NA",
            },
            {
                "jira_id": "PROJ-123",
                "test_case_id": "AdditionalPurchase_002",
                "module": "AdditionalPurchase",
                "sub_module": "Existing Strategy - Investor Portal",
                "priority": "HIGH",
                "type": "Regression",
                "test_case_description": "Validate Additional Purchase is blocked when PAN-holder AUM threshold is not satisfied",
                "preconditions": [
                    "1. Investor has active portal access with valid PAN and password",
                    "2. PAN-holder combination has existing DI code(s)",
                    "3. PAN-holder-combination AUM does NOT meet the 50 Lakh threshold",
                ],
                "test_steps": [
                    "1) Log in to Investor portal using PAN and password",
                    "2) Navigate to Additional Purchase module",
                    "3) Select PAN-holder combination mapped to ineligible AUM case",
                    "4) Attempt to enter purchase amount and proceed",
                    "5) Observe system validation response",
                ],
                "expected_results": [
                    "1) System blocks continuation for ineligible PAN-holder combination",
                    "2) Appropriate error message shown: AUM threshold not satisfied",
                    "3) No Additional Purchase request created in system",
                ],
                "postconditions": "No transaction created. System remains in stable browseable state.",
                "tags": "@regression",
                "automation_status": "Auto-Generated",
                "remarks": "Validates AUM threshold enforcement business rule. Generated autonomously. Jira: PROJ-123.",
                "scenario_nature": "Negative",
                "negative_category": "Business Rule",
            },
            {
                "jira_id": "PROJ-123",
                "test_case_id": "AdditionalPurchase_003",
                "module": "AdditionalPurchase",
                "sub_module": "Existing Strategy - Investor Portal",
                "priority": "MEDIUM",
                "type": "Regression",
                "test_case_description": "Validate boundary amount validation — amount exactly at minimum threshold passes",
                "preconditions": [
                    "1. Investor logged in with valid credentials",
                    "2. PAN-holder combination AUM satisfies threshold",
                    "3. Valid DI code selected",
                ],
                "test_steps": [
                    "1) Log in and navigate to Additional Purchase",
                    "2) Select eligible PAN-holder combination and DI code",
                    "3) Enter amount exactly at minimum: 5,00,000",
                    "4) Click Purchase and proceed through payment",
                    "5) Verify submission outcome",
                ],
                "expected_results": [
                    "1) Amount of exactly 5,00,000 passes validation",
                    "2) Transaction proceeds to payment screen",
                    "3) Submission successful with transaction reference",
                ],
                "postconditions": "Transaction created at boundary amount value.",
                "tags": "@regression",
                "automation_status": "Auto-Generated",
                "remarks": "Boundary value test at minimum amount. Generated autonomously. Jira: PROJ-123.",
                "scenario_nature": "Positive",
                "negative_category": "Boundary",
            },
            {
                "jira_id": "PROJ-123",
                "test_case_id": "AdditionalPurchase_004",
                "module": "AdditionalPurchase",
                "sub_module": "Existing Strategy - Investor Portal",
                "priority": "MEDIUM",
                "type": "Functional",
                "test_case_description": "Validate amount below minimum threshold is rejected with correct error message",
                "preconditions": [
                    "1. Investor logged in with valid credentials",
                    "2. PAN-holder combination AUM satisfies threshold",
                    "3. Valid DI code selected",
                ],
                "test_steps": [
                    "1) Log in and navigate to Additional Purchase",
                    "2) Select eligible PAN-holder combination and DI code",
                    "3) Enter amount below minimum: 4,00,000",
                    "4) Attempt to click Purchase button",
                    "5) Observe validation response",
                ],
                "expected_results": [
                    "1) Amount below minimum rejected with validation error",
                    "2) Error message specifies minimum amount requirement",
                    "3) Purchase button remains disabled or submission blocked",
                ],
                "postconditions": "No transaction created. Form remains in editable state.",
                "tags": "@functional",
                "automation_status": "Auto-Generated",
                "remarks": "Amount boundary validation below minimum. Generated autonomously. Jira: PROJ-123.",
                "scenario_nature": "Negative",
                "negative_category": "Validation",
            },
        ]
    ),
    # test_script_ui is raw Playwright source (the LLM's real output for this
    # agent type is a complete .py file, not JSON) — reuses the exact
    # selectors from recordings/investor/login_happy_path.py, never invents
    # new ones, and adds assertions + negative-case test functions on top.
    "test_script_ui": '''"""
investor_login_PROJ-123 — Generated Playwright script (mock LLM output).
Built on top of recordings/investor/login_happy_path.py — same selectors,
new assertions and negative-case test functions added on top.
"""
import re

from playwright.async_api import Page, expect


async def test_investor_standard_login(page: Page) -> None:
    """Happy path: valid credentials on a previously verified device."""
    await page.goto("https://uat.example.com/investor/login")
    await page.fill('input[name="email"]', "retail.investor@uat.example.com")
    await page.fill('input[name="password"]', "Test@1234")
    await page.click('button:has-text("Login")')
    await page.wait_for_load_state("networkidle")
    await page.wait_for_url(re.compile(r".*/investor/dashboard"))
    await expect(page).to_have_url(re.compile(r".*/investor/dashboard"))


async def test_investor_login_invalid_password(page: Page) -> None:
    """Negative: wrong password shows the invalid-credentials error."""
    await page.goto("https://uat.example.com/investor/login")
    await page.fill('input[name="email"]', "retail.investor@uat.example.com")
    await page.fill('input[name="password"]', "WrongPassword1")
    await page.click('button:has-text("Login")')
    await page.wait_for_load_state("networkidle")
    await expect(page.get_by_text("Invalid email or password")).to_be_visible()


async def test_investor_login_locked_account(page: Page) -> None:
    """Negative: account locked after repeated failed attempts."""
    await page.goto("https://uat.example.com/investor/login")
    await page.fill('input[name="email"]', "retail.investor@uat.example.com")
    await page.fill('input[name="password"]', "WrongPassword1")
    await page.click('button:has-text("Login")')
    await page.wait_for_load_state("networkidle")
    await expect(page.get_by_text("Your account has been locked")).to_be_visible()
''',
    # test_script_api mirrors postman_collections/investor/login.postman_collection.json
    # with 401/410 negative variants appended for each original request.
    "test_script_api": json.dumps(
        {
            "info": {
                "name": "Investor Login",
                "_postman_id": "b6f2e3a0-investor-login-0001",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [
                {
                    "name": "POST /api/v1/investor/login",
                    "request": {
                        "method": "POST",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "body": {
                            "mode": "raw",
                            "raw": '{"email": "retail.investor@uat.example.com", "password": "Test@1234", "device_id": "{{device_id}}"}',
                        },
                        "url": {"raw": "{{base_url}}/api/v1/investor/login"},
                    },
                },
                {
                    "name": "POST /api/v1/investor/login — invalid password",
                    "request": {
                        "method": "POST",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "body": {
                            "mode": "raw",
                            "raw": '{"email": "retail.investor@uat.example.com", "password": "wrong", "device_id": "{{device_id}}"}',
                        },
                        "url": {"raw": "{{base_url}}/api/v1/investor/login"},
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "exec": [
                                    "pm.test('Status code is 401', function () { pm.response.to.have.status(401); });"
                                ]
                            },
                        }
                    ],
                },
                {
                    "name": "POST /api/v1/investor/verify-otp",
                    "request": {
                        "method": "POST",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "body": {
                            "mode": "raw",
                            "raw": '{"otp": "123456", "session_token": "{{session_token}}"}',
                        },
                        "url": {"raw": "{{base_url}}/api/v1/investor/verify-otp"},
                    },
                },
                {
                    "name": "POST /api/v1/investor/verify-otp — expired OTP",
                    "request": {
                        "method": "POST",
                        "header": [{"key": "Content-Type", "value": "application/json"}],
                        "body": {
                            "mode": "raw",
                            "raw": '{"otp": "000000", "session_token": "{{session_token}}"}',
                        },
                        "url": {"raw": "{{base_url}}/api/v1/investor/verify-otp"},
                    },
                    "event": [
                        {
                            "listen": "test",
                            "script": {
                                "exec": [
                                    "pm.test('Status code is 410', function () { pm.response.to.have.status(410); });"
                                ]
                            },
                        }
                    ],
                },
            ],
            "variable": [
                {"key": "base_url", "value": "https://uat.example.com"},
                {"key": "device_id", "value": "uat-test-device-001"},
                {"key": "session_token", "value": ""},
            ],
        }
    ),
    "self_heal": json.dumps(
        {
            "candidate_selectors": [
                'button:has-text("Resend OTP")',
                "[aria-label='Resend OTP']",
                "text=Resend Code",
            ]
        }
    ),
    "generic": json.dumps({"message": "Mock LLM response — no agent_type matched."}),
}


class LLMRetryError(RuntimeError):
    """Raised when the LLM call fails after all retry attempts are exhausted."""


def _openai_retryable_errors() -> tuple[type[Exception], ...]:
    """Lazily import OpenAI's retryable exception types (azure/openai providers only)."""
    from openai import APIError, RateLimitError

    return (RateLimitError, APIError)


def _mock_invoke(agent_type: str) -> str:
    """Return the hardcoded mock response for the given agent type."""
    response = _MOCK_RESPONSES.get(agent_type, _MOCK_RESPONSES["generic"])
    logger.info(
        "[llm_client] USE_MOCK_LLM=true — returning mock response for agent_type=%s",
        agent_type,
    )
    return response


def _call_org_gateway(
    messages: list[dict[str, str]],
    max_tokens: int = 2000,
    temperature: float = 0,
) -> str:
    """
    Call the org's custom Azure OpenAI gateway endpoint via raw HTTP POST.

    Bypasses the LangChain/Azure SDK: this gateway uses a custom body
    format (a required stop field alongside standard params) and needs no
    API key — auth is handled by the org network (Zscaler/VPN). Only used
    when LLM_PROVIDER=org_gateway.
    """
    if not ORG_LLM_ENDPOINT:
        raise ValueError(
            "[llm_client] ORG_LLM_ENDPOINT not set in .env\n"
            "Set it to the full endpoint URL provided by your org."
        )

    headers = {"Content-Type": "application/json"}
    payload = {
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stop": "None",
    }

    logger.info("[llm_client] Calling org gateway: %s...", ORG_LLM_ENDPOINT[:70])
    response = requests.post(url=ORG_LLM_ENDPOINT, headers=headers, json=payload, timeout=60)
    response.raise_for_status()
    data = response.json()
    return str(data["choices"][0]["message"]["content"])


def _build_llm():
    """
    Build Azure OpenAI client using org-provided endpoint.
    No personal API key required — auth managed by org.

    AZURE_AUTH_MODE=managed_identity → Azure AD DefaultAzureCredential (Scenario A)
    AZURE_AUTH_MODE=gateway          → Org network gateway, no auth header (Scenario B)
    """
    if LLM_PROVIDER == "azure":
        from langchain_openai import AzureChatOpenAI

        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o")
        api_ver = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
        auth_mode = os.getenv("AZURE_AUTH_MODE", "gateway").lower()

        if not endpoint:
            raise ValueError(
                "[llm_client] AZURE_OPENAI_ENDPOINT not set in .env\n"
                "Ask your org for the Azure OpenAI endpoint URL."
            )

        if auth_mode == "managed_identity":
            # Scenario A — Azure AD managed identity
            # Machine must be Azure AD joined or running in Azure
            # Needs: pip install azure-identity
            logger.info("[llm_client] Azure auth: managed identity (Azure AD)")
            try:
                from azure.identity import (
                    DefaultAzureCredential,
                    get_bearer_token_provider,
                )

                credential = DefaultAzureCredential()
                token_provider = get_bearer_token_provider(
                    credential,
                    "https://cognitiveservices.azure.com/.default",
                )
                return AzureChatOpenAI(
                    azure_deployment=deployment,
                    azure_endpoint=endpoint,
                    api_version=api_ver,
                    azure_ad_token_provider=token_provider,
                    temperature=0,
                )
            except ImportError:
                raise ImportError(
                    "[llm_client] azure-identity package not installed.\n"
                    "Run: pip install azure-identity>=1.15.0"
                )

        else:
            # Scenario B — org gateway manages auth at network level
            # Endpoint just works when called from org network (Zscaler/VPN)
            # api_key param required by SDK but intercepted/ignored by gateway
            logger.info("[llm_client] Azure auth: org gateway (no personal API key)")
            return AzureChatOpenAI(
                azure_deployment=deployment,
                azure_endpoint=endpoint,
                api_version=api_ver,
                api_key="org-managed",  # SDK requires this param — gateway ignores it
                temperature=0,
            )

    else:
        # Standard OpenAI fallback — only if LLM_PROVIDER=openai
        from langchain_openai import ChatOpenAI

        logger.info("[llm_client] Using standard OpenAI")
        return ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0,
        )


def _real_invoke(messages: list[dict[str, str]]) -> str:
    """Call the configured LLM provider and return the response text content."""
    if LLM_PROVIDER == "org_gateway":
        return _call_org_gateway(messages)

    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

    llm = _build_llm()
    role_to_message = {"system": SystemMessage, "assistant": AIMessage}
    lc_messages = [
        role_to_message.get(m.get("role", "user"), HumanMessage)(content=m.get("content", ""))
        for m in messages
    ]
    result = llm.invoke(lc_messages)
    return str(result.content)


def invoke_with_retry(
    messages: list[dict[str, str]],
    agent_type: str = "generic",
    max_attempts: int = 3,
) -> str:
    """Invoke the LLM, retrying on transient errors, or return a mock.

    When USE_MOCK_LLM=true (default), returns a hardcoded, valid-JSON mock
    response for agent_type with no network call and no API key required.
    When USE_MOCK_LLM=false, calls the provider selected by LLM_PROVIDER
    (azure|openai|org_gateway), retrying on transient errors (rate limits,
    502/503/429, timeouts, connection errors) with exponential backoff
    (1s, 2s, 4s). Non-retryable HTTP errors (e.g. 400/401/404) raise
    immediately.

    Reads USE_MOCK_LLM from the environment on every call (not just at
    import time) so a change to the env var takes effect immediately even
    if another module imported this function earlier.
    """
    use_mock_llm = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    if use_mock_llm:
        return _mock_invoke(agent_type)

    provider = os.getenv("LLM_PROVIDER", "azure").lower()
    delay = 1.0
    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                "[llm_client] Attempt %d/%d — calling provider=%s agent_type=%s",
                attempt,
                max_attempts,
                provider,
                agent_type,
            )
            return _real_invoke(messages)
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else 0
            if status not in (429, 502, 503):
                logger.error("[llm_client] HTTP %s — not retrying: %s", status, str(e))
                raise
            last_error = e
            logger.warning(
                "[llm_client] Attempt %d/%d — HTTP %s, retrying", attempt, max_attempts, status
            )
            if attempt < max_attempts:
                time.sleep(delay)
                delay *= 2
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            logger.warning(
                "[llm_client] Attempt %d/%d — network error: %s", attempt, max_attempts, str(e)
            )
            if attempt < max_attempts:
                time.sleep(delay)
                delay *= 2
        except _openai_retryable_errors() as e:
            last_error = e
            logger.warning(
                "[llm_client] Attempt %d/%d failed: %s", attempt, max_attempts, str(e)
            )
            if attempt < max_attempts:
                time.sleep(delay)
                delay *= 2

    logger.error("[llm_client] All %d attempts failed: %s", max_attempts, str(last_error))
    raise LLMRetryError(f"LLM call failed after {max_attempts} attempts: {last_error}")
