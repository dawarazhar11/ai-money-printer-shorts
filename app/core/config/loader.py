"""YAML load/save and .env merge for ReelForge config.

Adapted from Pixelle-Video's pixelle_video/config/loader.py (Apache 2.0). We
add a small layer that maps existing `.env` variables onto the new YAML schema
so people who already configured `.env` don't have to redo their setup.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from app.core.logging import get_logger

logger = get_logger("config.loader")


# Map of env var → dotted YAML path. Kept small and explicit.
_ENV_OVERLAY: dict[str, str] = {
    "COMFYUI_IMAGE_API_URL": "comfyui.image_api_url",
    "COMFYUI_VIDEO_API_URL": "comfyui.video_api_url",
    "COMFYUI_WS_HOST": "comfyui.ws_host",
    "COMFYUI_WS_PORT": "comfyui.ws_port",
    "COMFYUI_API_KEY": "comfyui.api_key",
    "RUNNINGHUB_API_KEY": "comfyui.runninghub_api_key",
    "OLLAMA_API_URL": "ollama.api_url",
    "OLLAMA_MODEL": "ollama.model",
    "HEYGEN_API_KEY": "heygen.api_key",
    "HEYGEN_AVATAR_ID": "heygen.default_avatar_id",
    "HEYGEN_VOICE_ID": "heygen.default_voice_id",
    "REPLICATE_API_TOKEN": "replicate.api_token",
    "OPENAI_API_KEY": "llm.api_key",
    "OPENAI_BASE_URL": "llm.base_url",
    "OPENAI_MODEL": "llm.model",
}


def load_config_dict(config_path: str = "config.yaml") -> dict[str, Any]:
    """Load YAML config and overlay environment variables on top.

    Order of precedence (lowest → highest):
        Pydantic defaults  <  YAML file  <  .env / OS environment
    """
    load_dotenv(override=False)
    data: dict[str, Any] = {}

    config_file = Path(config_path)
    if config_file.exists():
        try:
            with config_file.open("r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            logger.info(f"Loaded YAML config: {config_path}")
        except Exception as exc:
            logger.error(f"Failed to parse {config_path}: {exc}")
    else:
        logger.info(f"No {config_path} found; starting from defaults + env")

    _apply_env_overlay(data)
    return data


def save_config_dict(config: dict[str, Any], config_path: str = "config.yaml") -> None:
    try:
        with open(config_path, "w", encoding="utf-8") as fh:
            yaml.dump(config, fh, allow_unicode=True, default_flow_style=False, sort_keys=False)
        logger.info(f"Saved config to {config_path}")
    except Exception as exc:
        logger.error(f"Failed to save {config_path}: {exc}")
        raise


def _apply_env_overlay(data: dict[str, Any]) -> None:
    """Mutate `data` in place, applying any matching env vars from _ENV_OVERLAY."""
    for env_name, dotted_path in _ENV_OVERLAY.items():
        value = os.environ.get(env_name)
        if value is None or value == "":
            continue
        _set_dotted(data, dotted_path, _coerce(value))


def _coerce(raw: str) -> Any:
    """Cheap coercion for ints / floats coming from env strings."""
    if raw.isdigit():
        return int(raw)
    try:
        return float(raw) if "." in raw and raw.replace(".", "", 1).isdigit() else raw
    except ValueError:
        return raw


def _set_dotted(data: dict[str, Any], dotted: str, value: Any) -> None:
    parts = dotted.split(".")
    cursor = data
    for part in parts[:-1]:
        if part not in cursor or not isinstance(cursor[part], dict):
            cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value
