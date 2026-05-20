"""Singleton ConfigManager with hot reload + deep-merge updates.

Adapted from Pixelle-Video's pixelle_video/config/manager.py (Apache 2.0).
Adds typed accessors for ReelForge-specific subsystems (HeyGen, Replicate,
Publishing) on top of the LLM/ComfyUI ones inherited from Pixelle.
"""

from __future__ import annotations

import os
from pathlib import Path
from threading import Lock
from typing import Any, Optional

from core.logging import get_logger

from .loader import load_config_dict, save_config_dict
from .schema import ReelForgeConfig

logger = get_logger("config.manager")


def _deep_merge(base: dict, updates: dict) -> dict:
    for key, value in updates.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
    return base


class ConfigManager:
    _instance: Optional["ConfigManager"] = None
    _lock = Lock()

    def __new__(cls, config_path: str = "config.yaml"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, config_path: str = "config.yaml"):
        if getattr(self, "_initialized", False):
            return
        self.config_path = Path(os.environ.get("REELFORGE_CONFIG", config_path))
        self.config: ReelForgeConfig = self._load()
        self._initialized = True

    # ── lifecycle ──────────────────────────────────────────────────────────

    def _load(self) -> ReelForgeConfig:
        data = load_config_dict(str(self.config_path))
        return ReelForgeConfig(**data)

    def reload(self) -> None:
        self.config = self._load()
        logger.info("Configuration reloaded")

    def save(self) -> None:
        save_config_dict(self.config.to_dict(), str(self.config_path))

    # ── mutation ───────────────────────────────────────────────────────────

    def update(self, updates: dict[str, Any]) -> None:
        merged = _deep_merge(self.config.to_dict(), updates)
        self.config = ReelForgeConfig(**merged)

    # ── typed shortcuts ────────────────────────────────────────────────────

    def llm(self):
        return self.config.llm

    def ollama(self):
        return self.config.ollama

    def comfyui(self):
        return self.config.comfyui

    def heygen(self):
        return self.config.heygen

    def replicate(self):
        return self.config.replicate

    def publishing(self):
        return self.config.publishing

    def storage(self):
        return self.config.storage


# module-level singleton; import as `from app.core.config import config_manager`
config_manager = ConfigManager()
