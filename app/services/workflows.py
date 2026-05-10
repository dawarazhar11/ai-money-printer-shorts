from pathlib import Path
from typing import List, Optional

from app.core.config import config_manager
from app.core.logging import get_logger

logger = get_logger("services.workflows")

_SEARCH_DIRS = ["selfhost", "cloud", ""]


def resolve(name: str) -> Optional[Path]:
    """Return the Path for a named workflow, searching subdirs then root."""
    wdir = config_manager.config.workflows_dir
    for subdir in _SEARCH_DIRS:
        candidate = wdir / subdir / name if subdir else wdir / name
        if candidate.exists():
            return candidate
        with_json = candidate.with_suffix(".json") if not candidate.suffix else candidate
        if with_json.exists():
            return with_json
    logger.warning("Workflow not found: %s", name)
    return None


def discover() -> List[Path]:
    """Return all .json workflow files across the workflow directory tree."""
    wdir = config_manager.config.workflows_dir
    if not wdir.exists():
        return []
    return sorted(wdir.rglob("*.json"))


def list_all() -> List[str]:
    """Return workflow names (stems) available in the workflow directory."""
    return [p.stem for p in discover()]
