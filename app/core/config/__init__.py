"""Pydantic-validated configuration for ReelForge.

Adapted from Pixelle-Video's pixelle_video.config (Apache 2.0). The schema is
extended for ReelForge's stack:
  - HeyGenConfig (avatar A-Roll)
  - ReplicateConfig (cloud B-Roll)
  - OllamaConfig (local LLM for prompt/script generation)
  - PublishingConfig (YouTube / TikTok / Instagram credentials)

Usage:
    from app.core.config import config_manager
    cfg = config_manager.config           # full ReelForgeConfig
    api_key = cfg.heygen.api_key
    config_manager.update({"llm": {"model": "qwen-max"}})
    config_manager.save()
"""

from .manager import ConfigManager, config_manager
from .schema import (
    ComfyUIConfig,
    HeyGenConfig,
    LLMConfig,
    OllamaConfig,
    PublishingConfig,
    ReelForgeConfig,
    ReplicateConfig,
    TemplateConfig,
    TTSConfig,
)

__all__ = [
    "ConfigManager",
    "config_manager",
    "ComfyUIConfig",
    "HeyGenConfig",
    "LLMConfig",
    "OllamaConfig",
    "PublishingConfig",
    "ReelForgeConfig",
    "ReplicateConfig",
    "TemplateConfig",
    "TTSConfig",
]
