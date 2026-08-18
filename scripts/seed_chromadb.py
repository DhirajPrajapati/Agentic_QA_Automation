"""
seed_chromadb — Loads known issues into the ChromaDB qa_learnings collection.
Part of: QA Orchestrator
Phase: 3
Mock-safe: n/a (ChromaDB is always real, local-only, no credentials needed)
"""
import argparse
import json
import logging
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_SEED_FILE = Path("mock_data/chromadb_seed/known_issues.json")
_SEED_SOURCE_ID = "manual_seed"


def _reset_collection() -> None:
    """Delete and recreate the qa_learnings collection."""
    import tools.chromadb_client as chromadb_client

    chromadb_client._client.delete_collection(name="qa_learnings")
    chromadb_client.collection = chromadb_client._client.get_or_create_collection(
        name="qa_learnings"
    )
    logger.info("[seed_chromadb] Collection reset")


def _already_seeded(module: str, document: str) -> bool:
    """Check whether this exact known-issue document was already seeded."""
    from tools.chromadb_client import collection

    existing = collection.get(
        where={"$and": [{"module": module}, {"source": _SEED_SOURCE_ID}]}
    )
    return document in (existing.get("documents") or [])


def main() -> None:
    """Seed known issues from mock_data/chromadb_seed/known_issues.json."""
    parser = argparse.ArgumentParser(description="Seed the ChromaDB qa_learnings collection")
    parser.add_argument(
        "--reset", action="store_true", help="Delete and recreate the collection before seeding"
    )
    args = parser.parse_args()

    if args.reset:
        _reset_collection()

    from tools.chromadb_client import CHROMADB_PATH, write_learning

    issues = json.loads(_SEED_FILE.read_text())

    seeded = 0
    for issue in issues:
        module = issue["module"]
        document = issue["document"]
        if _already_seeded(module, document):
            logger.info("[seed_chromadb] Skipping already-seeded document for %s", module)
            continue

        write_learning(
            document,
            {
                "module": module,
                "jira_id": "SEED",
                "run_date": "seed",
                "confidence": issue.get("confidence", 0.75),
                "source": _SEED_SOURCE_ID,
                "type": "known_issue",
            },
        )
        seeded += 1

    print(f"Seeded {seeded} documents to ChromaDB collection: qa_learnings")
    print(f"ChromaDB path: {CHROMADB_PATH}")


if __name__ == "__main__":
    main()
