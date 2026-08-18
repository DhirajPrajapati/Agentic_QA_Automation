"""
confluence_client — Fetch Confluence module knowledge. Mock/real per USE_MOCK.
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

_MODULE_MAP_PATH = Path("config/module_map.json")


def resolve_page_ids(labels: list[str]) -> list[str]:
    """Resolve Jira labels to Confluence page ids via config/module_map.json."""
    module_map: dict[str, dict[str, str]] = json.loads(_MODULE_MAP_PATH.read_text())
    label_set = set(labels)
    page_ids: list[str] = []
    for user_type, modules in module_map.items():
        if user_type not in label_set:
            continue
        for module_label, page_id in modules.items():
            if module_label in label_set and page_id not in page_ids:
                page_ids.append(page_id)
    logger.info("[confluence_client] Resolved labels %s -> page ids %s", labels, page_ids)
    return page_ids


def get_page_by_id(page_id: str) -> str:
    """Fetch a Confluence page's plain text content by page id."""
    if USE_MOCK:
        path = Path(f"mock_data/confluence/{page_id}.txt")
        logger.info("[confluence_client] Loading mock page: %s", path)
        return path.read_text()

    from atlassian import Confluence
    from bs4 import BeautifulSoup

    client = Confluence(
        url=os.getenv("CONFLUENCE_BASE_URL"),
        username=os.getenv("CONFLUENCE_EMAIL"),
        password=os.getenv("CONFLUENCE_API_TOKEN"),
    )
    logger.info("[confluence_client] Fetching real page: %s", page_id)
    page = client.get_page_by_id(page_id, expand="body.storage")
    html = page["body"]["storage"]["value"]
    return BeautifulSoup(html, "html.parser").get_text()
