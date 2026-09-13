"""
chromadb_client — Persistent vector memory for past failures and healed selectors.
Part of: QA Orchestrator
Phase: 6
Mock-safe: n/a (ChromaDB is always real; PersistentClient locally, HttpClient in Docker)
"""
import logging
import os
import uuid
from datetime import datetime

import chromadb
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

CHROMADB_PATH: str = os.getenv("CHROMADB_PATH", "./memory/chromadb")


def _create_client() -> chromadb.ClientAPI:
    """Build the ChromaDB client.

    When CHROMADB_HOST is set (Docker / server deployment) an HttpClient
    pointing at the chroma container is returned.  Otherwise a local
    PersistentClient is used (dev laptop, CI).
    """
    host = os.getenv("CHROMADB_HOST")
    if host:
        port = int(os.getenv("CHROMADB_PORT", "8000"))
        logger.info("[chromadb] Using remote server at %s:%d", host, port)
        return chromadb.HttpClient(host=host, port=port)
    return chromadb.PersistentClient(
        path=CHROMADB_PATH,
        settings=chromadb.Settings(anonymized_telemetry=False),
    )


_client = _create_client()
collection = _client.get_or_create_collection(name="qa_learnings")


def query_past_failures(module: str, summary: str, n: int = 5) -> list[str]:
    """Query ChromaDB for past learnings relevant to this module and ticket."""
    try:
        results = collection.query(
            query_texts=[f"{module} {summary}"],
            n_results=n,
            where={"module": module},
        )
    except Exception as e:
        logger.error("[chromadb] Query failed: %s", str(e))
        return []

    if not results["documents"] or not results["documents"][0]:
        return []
    return results["documents"][0]


def write_learning(doc: str, metadata: dict) -> None:
    """Write a learning document to ChromaDB after a test run.

    metadata must include: jira_id, module, run_date.
    """
    doc_id = f"run_{metadata.get('jira_id', 'unknown')}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
    collection.add(
        documents=[doc],
        metadatas=[{**metadata, "stored_at": datetime.now().isoformat()}],
        ids=[doc_id],
    )
    logger.info("[chromadb] Learning written: %s", doc_id)


def write_healed_selector(original: str, healed: str, module: str, element: str) -> None:
    """Write a healed selector to ChromaDB for future runs.

    Confidence starts at 0.85 for first healing.
    """
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
        "type": "healed_selector",
    }
    collection.add(
        documents=[doc],
        metadatas=[meta],
        ids=[f"heal_{module.replace('/', '_')}_{uuid.uuid4().hex[:8]}"],
    )
    logger.info("[chromadb] Healed selector written: %s → %s", original, healed)


def get_healed_selectors(module: str) -> dict[str, str]:
    """Retrieve all previously healed selectors for a module.

    Returns dict: {original_selector: healed_selector}
    """
    try:
        results = collection.get(
            where={"$and": [{"module": module}, {"type": "healed_selector"}]}
        )
    except Exception as e:
        logger.error("[chromadb] get_healed_selectors failed: %s", str(e))
        return {}

    healed = {}
    if results["metadatas"]:
        for meta in results["metadatas"]:
            healed[meta["original_selector"]] = meta["healed_selector"]
    return healed
