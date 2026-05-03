"""Legacy module-level config constants.

Kept for backward compatibility with pages that import:
    from config import COMFYUI_IMAGE_API_URL  # etc.

New code should use the typed singleton instead:
    from app.core.config import config_manager
    config_manager.comfyui().image_api_url
"""

from pathlib import Path

from app.core.config import config_manager

_cfg = config_manager.config

# ── ComfyUI ────────────────────────────────────────────────────────────────
COMFYUI_IMAGE_API_URL = _cfg.comfyui.image_api_url
COMFYUI_VIDEO_API_URL = _cfg.comfyui.video_api_url
COMFYUI_WS_HOST = _cfg.comfyui.ws_host
COMFYUI_WS_PORT = str(_cfg.comfyui.ws_port)

# ── Ollama ─────────────────────────────────────────────────────────────────
OLLAMA_API_URL = _cfg.ollama.api_url

# ── HeyGen ─────────────────────────────────────────────────────────────────
HEYGEN_API_KEY = _cfg.heygen.api_key

# ── Replicate ──────────────────────────────────────────────────────────────
REPLICATE_API_TOKEN = _cfg.replicate.api_token

# ── Paths ──────────────────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = APP_DIR.parent
WORKFLOWS_DIR = APP_DIR / "workflows"
FONTS_DIR = APP_DIR / "fonts"
MEDIA_DIR = APP_DIR / "media"
USER_DATA_DIR = APP_DIR / "config" / "user_data"
TEMPLATES_DIR = APP_DIR / "templates"
