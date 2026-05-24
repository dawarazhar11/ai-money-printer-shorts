import os
import sys
from pathlib import Path
from typing import Optional

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.heygen_service")

try:
    from tenacity import retry, stop_after_attempt, wait_random_exponential
    _TENACITY_AVAILABLE = True
except ImportError:
    _TENACITY_AVAILABLE = False

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

try:
    from utils.heygen_api import HeyGenAPI
    _HEYGEN_AVAILABLE = True
except ImportError:
    _HEYGEN_AVAILABLE = False
    logger.warning("utils.heygen_api not importable — HeyGen synthesis unavailable")


class HeyGenService:
    def _client(self) -> "HeyGenAPI":
        if not _HEYGEN_AVAILABLE:
            raise RuntimeError("utils.heygen_api not importable")
        api_key = config_manager.config.heygen_api_key
        if not api_key:
            raise RuntimeError("HEYGEN_API_KEY is not configured")
        return HeyGenAPI(api_key)

    def synthesize_avatar(
        self,
        text: str,
        avatar_id: str,
        voice_id: str,
        avatar_type: str = "video",
        output_dir: Optional[str] = None,
    ) -> dict:
        """Submit a HeyGen video generation job. Returns a dict with video_id for polling."""
        client = self._client()
        logger.info("Submitting HeyGen job: avatar=%s voice=%s", avatar_id, voice_id)
        if avatar_type == "photo":
            result = client.create_talking_photo(text=text, avatar_id=avatar_id, voice_id=voice_id)
        else:
            result = client.create_talking_video(text=text, avatar_id=avatar_id, voice_id=voice_id)
        if result.get("status") != "success":
            raise RuntimeError(f"HeyGen API error: {result.get('message', 'unknown')}")
        return result

    def check_status(self, video_id: str) -> dict:
        client = self._client()
        logger.info("Checking HeyGen status: %s", video_id)
        return client.check_video_status(video_id)

    def download_video(self, video_url: str, output_path: str) -> MediaAsset:
        client = self._client()
        logger.info("Downloading HeyGen video -> %s", output_path)
        result = client.download_video(video_url, output_path)
        if result.get("status") != "success":
            raise RuntimeError(f"Download failed: {result.get('message', 'unknown')}")
        return MediaAsset(path=output_path, asset_type="video")


heygen_service = HeyGenService()
