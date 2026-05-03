"""Edge-TTS service: free text-to-speech for A-Roll narration.

Adapted from Pixelle-Video's pixelle_video/utils/tts_util.py and
services/tts_service.py (Apache 2.0). Differences from upstream:

  - No ComfyUI branch in this module (TTS via ComfyUI lives in
    `services/comfy_tts_service.py` once we wire it up).
  - tenacity replaces the hand-rolled retry loop — same exponential
    backoff + jitter, less code, easier to test.
  - Sync wrappers (`synthesize_sync`) so Streamlit pages can call
    this without managing event loops; async API is still exposed for
    the future FastAPI surface.

Edge-TTS itself requires no API key — it's a free Microsoft service that
exposes 400+ neural voices across 100+ languages.
"""

from __future__ import annotations

import asyncio
import ssl
import subprocess
import uuid
from pathlib import Path
from typing import Optional

import certifi
import edge_tts as edge_tts_sdk
from edge_tts.exceptions import NoAudioReceived
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)

from app.core.catalogs import get_voice, speed_to_rate
from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.tts")

# Concurrency cap — Edge-TTS rate-limits aggressive callers with HTTP 401.
_MAX_CONCURRENT = 3
_RETRY_ATTEMPTS = 5
_REQUEST_DELAY = 0.5  # seconds, baseline jitter before each request


class EdgeTTSService:
    """Free Microsoft Edge-TTS wrapper.

    Use this as the default A-Roll backend when HeyGen credit isn't
    available. Output is MP3 at the same bitrate Edge produces (~24 kbps).
    """

    def __init__(self) -> None:
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._semaphore_loop: Optional[asyncio.AbstractEventLoop] = None

    # ── public API ──────────────────────────────────────────────────────────

    async def synthesize(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        output_path: Optional[Path] = None,
    ) -> MediaAsset:
        """Synthesize MP3 audio for `text`. Returns a persisted MediaAsset."""
        cfg = config_manager.config.tts.local
        final_voice = voice or cfg.voice
        final_speed = speed if speed is not None else cfg.speed
        if get_voice(final_voice) is None:
            logger.warning(f"voice '{final_voice}' not in catalog — passing through to Edge")

        rate = speed_to_rate(final_speed)
        target = self._resolve_path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"TTS synthesize voice={final_voice} rate={rate} -> {target}")
        audio_bytes = await self._synthesize_with_retry(text, final_voice, rate)
        target.write_bytes(audio_bytes)

        return MediaAsset(
            media_type="audio",
            backend="edge_tts",
            path=target,
            duration=_probe_duration(target),
            metadata={"voice": final_voice, "rate": rate, "speed": final_speed},
        )

    def synthesize_sync(
        self,
        text: str,
        voice: Optional[str] = None,
        speed: Optional[float] = None,
        output_path: Optional[Path] = None,
    ) -> MediaAsset:
        """Sync wrapper — Streamlit pages should call this one."""
        return asyncio.run(self.synthesize(text, voice, speed, output_path))

    # ── internals ───────────────────────────────────────────────────────────

    def _resolve_path(self, output_path: Optional[Path]) -> Path:
        if output_path is not None:
            return Path(output_path)
        media_root = Path(config_manager.storage().media_dir) / "edge_tts"
        return media_root / f"{uuid.uuid4().hex}.mp3"

    def _get_semaphore(self) -> asyncio.Semaphore:
        loop = asyncio.get_running_loop()
        if self._semaphore is None or self._semaphore_loop is not loop:
            self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT)
            self._semaphore_loop = loop
        return self._semaphore

    async def _synthesize_with_retry(self, text: str, voice: str, rate: str) -> bytes:
        async with self._get_semaphore():
            await asyncio.sleep(_REQUEST_DELAY)
            ssl_context = ssl.create_default_context(cafile=certifi.where())

            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(_RETRY_ATTEMPTS),
                wait=wait_random_exponential(multiplier=1.0, max=10.0),
                retry=retry_if_exception_type((NoAudioReceived, OSError)),
                reraise=True,
            ):
                with attempt:
                    return await self._synth_once(text, voice, rate, ssl_context)
            raise RuntimeError("unreachable")  # tenacity always raises or returns

    async def _synth_once(self, text: str, voice: str, rate: str, ssl_context) -> bytes:
        comm = edge_tts_sdk.Communicate(text=text, voice=voice, rate=rate)
        chunks: list[bytes] = []
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                chunks.append(chunk["data"])
        if not chunks:
            raise NoAudioReceived("Edge-TTS returned zero audio chunks")
        return b"".join(chunks)


def _probe_duration(path: Path) -> float:
    """Use ffprobe to get audio duration. Falls back to size-based estimate."""
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return float(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        # Rough estimate: 24 kbps Edge-TTS → ~3 KB per second
        return max(1.0, path.stat().st_size / 3000)


# module-level singleton — services should be cheap to import everywhere
edge_tts_service = EdgeTTSService()
