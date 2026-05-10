"""Pydantic-based config singleton for ReelForge."""
from __future__ import annotations

import os
from functools import cached_property
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel, Field

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

APP_DIR = Path(__file__).resolve().parent.parent


class ReelForgeConfig(BaseModel):
    # ComfyUI
    comfyui_image_api_url: str = Field(default_factory=lambda: os.getenv("COMFYUI_IMAGE_API_URL", "http://127.0.0.1:8000"))
    comfyui_video_api_url: str = Field(default_factory=lambda: os.getenv("COMFYUI_VIDEO_API_URL", "http://127.0.0.1:8001"))
    comfyui_ws_host: str = Field(default_factory=lambda: os.getenv("COMFYUI_WS_HOST", "127.0.0.1"))
    comfyui_ws_port: str = Field(default_factory=lambda: os.getenv("COMFYUI_WS_PORT", "8000"))

    # Ollama
    ollama_api_url: str = Field(default_factory=lambda: os.getenv("OLLAMA_API_URL", "http://127.0.0.1:11434/api"))

    # HeyGen
    heygen_api_key: str = Field(default_factory=lambda: os.getenv("HEYGEN_API_KEY", ""))

    # Replicate
    replicate_api_token: str = Field(default_factory=lambda: os.getenv("REPLICATE_API_TOKEN", ""))

    # Paths (computed, not configurable via env)
    app_dir: Path = APP_DIR
    workflows_dir: Path = APP_DIR / "workflows"
    fonts_dir: Path = APP_DIR / "fonts"
    media_dir: Path = APP_DIR / "media"
    user_data_dir: Path = APP_DIR / "config" / "user_data"

    model_config = {"arbitrary_types_allowed": True}

    def is_heygen_configured(self) -> bool:
        return bool(self.heygen_api_key)

    def is_replicate_configured(self) -> bool:
        return bool(self.replicate_api_token)

    def is_comfyui_configured(self) -> bool:
        return self.comfyui_image_api_url != "http://127.0.0.1:8000"


class _ConfigManager:
    """Lazy singleton — reads env once on first .config access."""

    @cached_property
    def config(self) -> ReelForgeConfig:
        return ReelForgeConfig()


config_manager = _ConfigManager()
