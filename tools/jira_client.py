"""
jira_client — Fetch Jira tickets. Mock/real per USE_MOCK.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

USE_MOCK: bool = os.getenv("USE_MOCK", "true").lower() == "true"


def get_ticket(jira_id: str) -> dict:
    """Fetch a Jira ticket by id. Loads from mock_data/jira when USE_MOCK=true."""
    if USE_MOCK:
        path = Path(f"mock_data/jira/{jira_id}.json")
        logger.info("[jira_client] Loading mock ticket: %s", path)
        return json.loads(path.read_text())

    from atlassian import Jira

    client = Jira(
        url=os.getenv("JIRA_BASE_URL"),
        username=os.getenv("JIRA_EMAIL"),
        password=os.getenv("JIRA_API_TOKEN"),
    )
    logger.info("[jira_client] Fetching real ticket: %s", jira_id)
    return client.issue(jira_id)


def post_comment(jira_id: str, comment: str) -> None:
    """Post a comment on a Jira ticket. Logs instead of posting when USE_MOCK=true."""
    if USE_MOCK:
        logger.info("[jira] MOCK: would post comment to %s", jira_id)
        return

    from atlassian import Jira

    client = Jira(
        url=os.getenv("JIRA_BASE_URL"),
        username=os.getenv("JIRA_EMAIL"),
        password=os.getenv("JIRA_API_TOKEN"),
    )
    client.issue_add_comment(jira_id, comment)
