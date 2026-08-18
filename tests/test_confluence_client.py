"""
test_confluence_client — Tests for tools/confluence_client.py.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import importlib

import pytest


@pytest.fixture
def confluence_client_mock_mode(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    import tools.confluence_client as confluence_client

    importlib.reload(confluence_client)
    return confluence_client


def test_resolve_page_ids_maps_investor_login_labels(confluence_client_mock_mode):
    page_ids = confluence_client_mock_mode.resolve_page_ids(["investor", "login", "otp"])
    assert "investor_login" in page_ids


def test_resolve_page_ids_deduplicates(confluence_client_mock_mode):
    page_ids = confluence_client_mock_mode.resolve_page_ids(["investor", "login", "otp"])
    assert page_ids.count("investor_login") == 1


def test_resolve_page_ids_ignores_unmatched_labels(confluence_client_mock_mode):
    page_ids = confluence_client_mock_mode.resolve_page_ids(["frontend", "nonexistent"])
    assert page_ids == []


def test_get_page_by_id_loads_mock_text(confluence_client_mock_mode):
    text = confluence_client_mock_mode.get_page_by_id("investor_login")
    assert len(text) > 100
    assert "OTP" in text
