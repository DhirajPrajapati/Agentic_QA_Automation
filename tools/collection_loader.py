"""
collection_loader — Load Postman collection files if present.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_collection(user_type: str, module: str) -> Optional[dict]:
    """Load a Postman collection JSON, or None if not found."""
    path = Path(f"postman_collections/{user_type}/{module}.postman_collection.json")
    if not path.exists():
        logger.info("[collection_loader] No collection found: %s", path)
        return None
    logger.info("[collection_loader] Collection found: %s", path)
    return json.loads(path.read_text())
