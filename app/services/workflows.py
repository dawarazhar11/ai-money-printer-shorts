"""Workflow path resolution for ComfyUI JSON workflow files."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.config import config_manager
from app.core.logging import get_logger

logger = get_logger("services.workflows")


def _workflows_root() -> Path:
    return config_manager.config.workflows_dir


def discover() -> list[Path]:
    """Return all .json workflow files under the workflows directory."""
    root = _workflows_root()
    if not root.exists():
        return []
    return sorted(root.rglob("*.json"))


def list_all() -> list[str]:
    """Return workflow names (stem of each .json file) found in the tree."""
    return [p.stem for p in discover()]


def resolve(name: str) -> Optional[Path]:
    """Find a workflow file by name (with or without .json extension).

    Searches the workflows directory recursively. Returns *None* when not found.
    """
    stem = name.removesuffix(".json")
    for p in discover():
        if p.stem == stem:
            logger.info(f"Resolved workflow '{name}' → {p}")
            return p
    logger.warning(f"Workflow not found: '{name}'")
    return None
