import asyncio
import tempfile
from pathlib import Path
from typing import Optional

from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.tts_service")

try:
    import edge_tts
    _EDGE_TTS_AVAILABLE = True
except ImportError:
    _EDGE_TTS_AVAILABLE = False
    logger.warning("edge-tts not installed — TTS synthesis unavailable")

try:
    from tenacity import retry, stop_after_attempt, wait_random_exponential
    _TENACITY_AVAILABLE = True
except ImportError:
    _TENACITY_AVAILABLE = False


def _retry(fn):
    if _TENACITY_AVAILABLE:
        from tenacity import retry as _r, stop_after_attempt, wait_random_exponential
        return _r(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, max=30))(fn)
    return fn


class EdgeTTSService:
    DEFAULT_VOICE = "en-US-AriaNeural"
    DEFAULT_SPEED = "+0%"

    def synthesize_sync(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[str] = None,
        output_path: Optional[str] = None,
    ) -> MediaAsset:
        if not _EDGE_TTS_AVAILABLE:
            raise RuntimeError("edge-tts is not installed. Run: pip install edge-tts")

        voice = voice or self.DEFAULT_VOICE
        speed = speed or self.DEFAULT_SPEED

        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            output_path = tmp.name
            tmp.close()

        logger.info("Synthesizing TTS: voice=%s speed=%s -> %s", voice, speed, output_path)
        asyncio.run(self._synthesize(text, voice, speed, output_path))
        return MediaAsset(path=output_path, asset_type="audio")

    async def _synthesize(self, text: str, voice: str, speed: str, output_path: str) -> None:
        communicate = edge_tts.Communicate(text, voice, rate=speed)
        await communicate.save(output_path)


edge_tts_service = EdgeTTSService()
