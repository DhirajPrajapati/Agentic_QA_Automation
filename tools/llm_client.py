"""
llm_client — Wrapper for Azure OpenAI / OpenAI LLM calls with mock support
and retry logic. Provider selected via LLM_PROVIDER (azure|openai).
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import json
import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

USE_MOCK_LLM: bool = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "azure").lower()

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
    "test_case": json.dumps(
        [
            {
                "id": "TC-001",
                "flow": "standard_login",
                "priority": "P1",
                "given": "User is on /investor/login",
                "when": "User enters valid email and password and clicks Login",
                "then": "User is redirected to /investor/dashboard",
                "type": "ui",
            },
            {
                "id": "TC-002",
                "flow": "standard_login",
                "priority": "P2",
                "given": "User is on /investor/login",
                "when": "User enters an invalid password and clicks Login",
                "then": "Error message 'Invalid email or password' is shown",
                "type": "ui",
            },
            {
                "id": "TC-003",
                "flow": "otp_trigger",
                "priority": "P1",
                "given": "User has entered valid credentials on a new device",
                "when": "Login is submitted",
                "then": "OTP screen is displayed within 5 seconds",
                "type": "ui",
            },
            {
                "id": "TC-004",
                "flow": "otp_verify",
                "priority": "P2",
                "given": "User is on the OTP verification screen",
                "when": "User enters an expired OTP",
                "then": "Error message 'OTP has expired' is shown",
                "type": "api",
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


def _mock_invoke(agent_type: str) -> str:
    """Return the hardcoded mock response for the given agent type."""
    response = _MOCK_RESPONSES.get(agent_type, _MOCK_RESPONSES["generic"])
    logger.info(
        "[llm_client] USE_MOCK_LLM=true — returning mock response for agent_type=%s",
        agent_type,
    )
    return response


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
    """Invoke the LLM, retrying on transient OpenAI errors, or return a mock.

    When USE_MOCK_LLM=true (default), returns a hardcoded, valid-JSON mock
    response for agent_type with no network call and no API key required.
    When USE_MOCK_LLM=false, calls OpenAI via ChatOpenAI, retrying on
    RateLimitError/APIError with exponential backoff (1s, 2s, 4s).

    Reads USE_MOCK_LLM from the environment on every call (not just at
    import time) so a change to the env var takes effect immediately even
    if another module imported this function earlier.
    """
    use_mock_llm = os.getenv("USE_MOCK_LLM", "true").lower() == "true"
    if use_mock_llm:
        return _mock_invoke(agent_type)

    from openai import APIError, RateLimitError

    delay = 1.0
    last_error: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                "[llm_client] Attempt %d/%d — calling OpenAI model=%s",
                attempt,
                max_attempts,
                OPENAI_MODEL,
            )
            return _real_invoke(messages)
        except (RateLimitError, APIError) as e:
            last_error = e
            logger.warning(
                "[llm_client] Attempt %d/%d failed: %s", attempt, max_attempts, str(e)
            )
            if attempt < max_attempts:
                time.sleep(delay)
                delay *= 2

    logger.error("[llm_client] All %d attempts failed: %s", max_attempts, str(last_error))
    raise LLMRetryError(f"LLM call failed after {max_attempts} attempts: {last_error}")
