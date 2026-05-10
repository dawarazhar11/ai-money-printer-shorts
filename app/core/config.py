import os
from pathlib import Path
from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)


class ReelForgeConfig:
    def __init__(self) -> None:
        self.comfyui_image_api_url: str = os.getenv("COMFYUI_IMAGE_API_URL", "http://127.0.0.1:8000")
        self.comfyui_video_api_url: str = os.getenv("COMFYUI_VIDEO_API_URL", "http://127.0.0.1:8001")
        self.comfyui_ws_host: str = os.getenv("COMFYUI_WS_HOST", "127.0.0.1")
        self.comfyui_ws_port: str = os.getenv("COMFYUI_WS_PORT", "8000")
        self.ollama_api_url: str = os.getenv("OLLAMA_API_URL", "http://127.0.0.1:11434/api")
        self.heygen_api_key: str = os.getenv("HEYGEN_API_KEY", "")
        self.replicate_api_token: str = os.getenv("REPLICATE_API_TOKEN", "")
        self.app_dir: Path = Path(__file__).resolve().parent.parent
        self.project_root: Path = self.app_dir.parent
        self.workflows_dir: Path = self.app_dir / "workflows"
        self.fonts_dir: Path = self.app_dir / "fonts"
        self.media_dir: Path = self.app_dir / "media"
        self.user_data_dir: Path = self.app_dir / "config" / "user_data"

    def is_heygen_configured(self) -> bool:
        return bool(self.heygen_api_key)

    def is_replicate_configured(self) -> bool:
        return bool(self.replicate_api_token)

    def is_comfyui_configured(self) -> bool:
        return True  # always attempts; fails at runtime if server is down


class _ConfigManager:
    _instance: "ReelForgeConfig | None" = None

    @property
    def config(self) -> ReelForgeConfig:
        if self._instance is None:
            self._instance = ReelForgeConfig()
        return self._instance

    def reload(self) -> None:
        self._instance = None


config_manager = _ConfigManager()
