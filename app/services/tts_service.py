"""Edge-TTS service with tenacity retries."""
from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

from tenacity import AsyncRetrying, stop_after_attempt, wait_random_exponential

from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.tts")

_DEFAULT_VOICE = "en-US-AriaNeural"
_DEFAULT_SPEED = "+0%"


class EdgeTTSService:
    async def synthesize(
        self,
        text: str,
        voice: str = _DEFAULT_VOICE,
        speed: str = _DEFAULT_SPEED,
        output_path: str | None = None,
    ) -> MediaAsset:
        import edge_tts

        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            output_path = tmp.name
            tmp.close()

        logger.info(f"TTS synthesize voice={voice} len={len(text)}")
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(5),
            wait=wait_random_exponential(multiplier=1, min=1, max=30),
            reraise=True,
        ):
            with attempt:
                communicate = edge_tts.Communicate(text=text, voice=voice, rate=speed)
                await communicate.save(output_path)

        logger.info(f"TTS done → {output_path}")
        return MediaAsset(file_path=output_path, mime_type="audio/mpeg")

    def synthesize_sync(
        self,
        text: str,
        voice: str = _DEFAULT_VOICE,
        speed: str = _DEFAULT_SPEED,
        output_path: str | None = None,
    ) -> MediaAsset:
        """Blocking wrapper around the async synthesize method."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self.synthesize(text, voice, speed, output_path))
                    return future.result()
            else:
                return loop.run_until_complete(self.synthesize(text, voice, speed, output_path))
        except RuntimeError:
            return asyncio.run(self.synthesize(text, voice, speed, output_path))


edge_tts_service = EdgeTTSService()
