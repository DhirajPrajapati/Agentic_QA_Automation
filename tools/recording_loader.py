"""
recording_loader — Load Playwright recording files if present.
Part of: QA Orchestrator
Phase: 1
Mock-safe: yes
"""
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def load_recording(user_type: str, module: str) -> Optional[str]:
    """Load a recorded Playwright script's source, or None if not found."""
    path = Path(f"recordings/{user_type}/{module}_happy_path.py")
    if not path.exists():
        logger.info("[recording_loader] No recording found: %s", path)
        return None
    logger.info("[recording_loader] Recording found: %s", path)
    return path.read_text()
