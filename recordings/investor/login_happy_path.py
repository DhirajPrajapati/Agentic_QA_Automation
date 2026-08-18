"""
login_happy_path — Recorded Playwright script for investor standard login.
Part of: QA Orchestrator
Phase: 1
Mock-safe: n/a (recording, not runtime code)

Simulates the output of the VS Code Playwright recorder against the legacy
investor portal. Selectors here are real baselines captured from the UI —
downstream agents must load and reuse them, never invent new ones.
"""
import re

from playwright.async_api import Page, expect


async def test_investor_standard_login(page: Page) -> None:
    """Recorded happy path: valid credentials on a previously verified device."""

    # Navigate to the investor login page on UAT.
    await page.goto("https://uat.example.com/investor/login")

    # Fill in the registered email address.
    await page.fill('input[name="email"]', "retail.investor@uat.example.com")

    # Fill in the account password.
    await page.fill('input[name="password"]', "Test@1234")

    # Click the Login button to submit credentials.
    await page.click('button:has-text("Login")')

    # Wait for redirect to the dashboard (existing/verified device path).
    await page.wait_for_url(re.compile(r".*/investor/dashboard"))

    # Confirm the dashboard actually loaded.
    await expect(page).to_have_url(re.compile(r".*/investor/dashboard"))
