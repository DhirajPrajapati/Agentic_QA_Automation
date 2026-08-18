"""
test_jira_client — Tests for tools/jira_client.py.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import importlib

import pytest


@pytest.fixture
def jira_client_mock_mode(monkeypatch):
    monkeypatch.setenv("USE_MOCK", "true")
    import tools.jira_client as jira_client

    importlib.reload(jira_client)
    return jira_client


def test_get_ticket_loads_mock_by_id(jira_client_mock_mode):
    ticket = jira_client_mock_mode.get_ticket("PROJ-123")
    assert ticket["id"] == "PROJ-123"


def test_get_ticket_includes_expected_fields(jira_client_mock_mode):
    ticket = jira_client_mock_mode.get_ticket("PROJ-123")
    assert "investor" in ticket["fields"]["labels"]
    assert ticket["fields"]["issuetype"]["name"] == "Bug"
    assert len(ticket["fields"]["acceptance_criteria"]) == 3
