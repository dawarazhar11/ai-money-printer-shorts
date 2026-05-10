"""HeyGen service — wraps utils/heygen_api.py with tenacity retries.

Provides a synthesize_avatar() interface mirroring edge_tts_service.synthesize_sync().
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.heygen")

_COMPLETED_STATUSES = {"completed", "ready", "success", "done"}


class HeyGenService:
    """Thin service layer over utils.heygen_api.HeyGenAPI."""

    def _get_client(self):
        from app.utils.heygen_api import HeyGenAPI
        api_key = config_manager.config.heygen_api_key or os.environ.get("HEYGEN_API_KEY", "")
        if not api_key:
            raise ValueError("HEYGEN_API_KEY is not configured")
        return HeyGenAPI(api_key)

    @retry(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, min=2, max=30), reraise=True)
    def _submit_video(self, client, text: str, avatar_id: str, voice_id: str, avatar_type: str) -> str:
        if avatar_type == "photo":
            result = client.create_talking_photo(text=text, avatar_id=avatar_id, voice_id=voice_id)
        else:
            result = client.create_talking_video(text=text, avatar_id=avatar_id, voice_id=voice_id)
        if result.get("status") != "success":
            raise RuntimeError(f"HeyGen submit failed: {result.get('message')}")
        video_id = result.get("data", {}).get("video_id") or result.get("video_id")
        if not video_id:
            raise RuntimeError("HeyGen returned no video_id")
        return video_id

    @retry(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, min=2, max=30), reraise=True)
    def _poll_status(self, client, video_id: str) -> dict:
        result = client.check_video_status(video_id)
        if result.get("status") != "success":
            raise RuntimeError(f"Status check failed: {result.get('message')}")
        data = result.get("data", {})
        status = data.get("status", "").lower()
        if status in ("failed", "failure", "error"):
            raise RuntimeError(f"HeyGen generation failed: {data.get('error')}")
        return data

    def synthesize_avatar(
        self,
        text: str,
        avatar_id: str,
        voice_id: str,
        avatar_type: str = "video",
        output_dir: Optional[Path] = None,
        segment_id: str = "segment",
    ) -> MediaAsset:
        """Generate a HeyGen avatar video synchronously and return a MediaAsset."""
        client = self._get_client()

        logger.info(f"Submitting HeyGen job for {segment_id}")
        video_id = self._submit_video(client, text, avatar_id, voice_id, avatar_type)
        logger.info(f"HeyGen video_id={video_id} — polling…")

        import time
        max_wait = 600
        elapsed = 0
        interval = 10
        while elapsed < max_wait:
            data = self._poll_status(client, video_id)
            status = data.get("status", "").lower()
            if status in _COMPLETED_STATUSES and data.get("video_url"):
                break
            logger.info(f"HeyGen status={status} ({elapsed}s elapsed)")
            time.sleep(interval)
            elapsed += interval
        else:
            raise TimeoutError(f"HeyGen timed out after {max_wait}s for video {video_id}")

        video_url = data["video_url"]
        if output_dir is None:
            output_dir = config_manager.config.media_dir / "a-roll"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"{segment_id}.mp4")

        logger.info(f"Downloading HeyGen video → {output_path}")
        dl = client.download_video(video_url, output_path)
        if dl.get("status") != "success":
            raise RuntimeError(f"Download failed: {dl.get('message')}")

        logger.info(f"HeyGen done → {output_path}")
        return MediaAsset(
            file_path=output_path,
            mime_type="video/mp4",
            metadata={"video_id": video_id, "heygen_url": video_url},
        )

    def check_video_status(self, video_id: str) -> dict:
        """Check HeyGen video status; returns raw data dict."""
        client = self._get_client()
        return self._poll_status(client, video_id)

    def download_video(self, video_url: str, output_path: str) -> dict:
        """Download a HeyGen video by URL."""
        client = self._get_client()
        return client.download_video(video_url, output_path)


heygen_service = HeyGenService()
