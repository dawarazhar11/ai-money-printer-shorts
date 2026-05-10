"""Video assembly service — wraps the moviepy/ffmpeg utilities into a clean interface."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Callable, Optional

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset, ProgressEvent

logger = get_logger("services.video_assembly")

_DEFAULT_RESOLUTION = (1080, 1920)


class VideoAssemblyService:
    """Assemble A-Roll and B-Roll segments into a single video file."""

    def assemble(
        self,
        sequence: list[dict],
        target_resolution: tuple[int, int] = _DEFAULT_RESOLUTION,
        output_dir: Optional[Path] = None,
        progress_cb: Optional[Callable[[ProgressEvent], None]] = None,
    ) -> MediaAsset:
        """Assemble *sequence* into a single video.

        Each item in *sequence* is a dict with:
          type: "aroll_full" | "broll_with_aroll_audio"
          aroll_path: str
          broll_path: str | None
          segment_id: str

        Tries MoviePy first, falls back to simple FFmpeg assembly.
        """
        if not sequence:
            raise ValueError("Assembly sequence is empty")

        if output_dir is None:
            output_dir = config_manager.config.user_data_dir / "output"
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        def _cb(progress: float, msg: str) -> None:
            if progress_cb:
                progress_cb(ProgressEvent(step="assembly", progress=progress, message=msg))

        _cb(0.0, "Starting assembly")

        # Try primary MoviePy assembler
        result = self._try_moviepy(sequence, target_resolution, output_dir, _cb)
        if result is None:
            logger.warning("MoviePy assembly failed, trying ffmpeg simple assembly")
            result = self._try_simple(sequence, target_resolution, output_dir, _cb)

        if result is None:
            raise RuntimeError("Both assembly methods failed — check logs for details")

        _cb(1.0, "Assembly complete")
        logger.info(f"Assembly output: {result}")
        return MediaAsset(file_path=result, mime_type="video/mp4")

    # ------------------------------------------------------------------
    def _try_moviepy(
        self,
        sequence: list[dict],
        resolution: tuple[int, int],
        output_dir: Path,
        cb: Callable,
    ) -> Optional[str]:
        try:
            import sys
            sys.path.insert(0, str(config_manager.config.app_dir))
            from utils.video.assembly import assemble_video, MOVIEPY_AVAILABLE

            if not MOVIEPY_AVAILABLE:
                return None

            from datetime import datetime
            output_path = str(output_dir / f"assembled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4")
            result = assemble_video(
                sequence=sequence,
                target_resolution=resolution,
                output_dir=str(output_dir),
                progress_callback=cb,
            )
            if isinstance(result, dict) and result.get("status") == "success":
                return result.get("output_path")
            return None
        except Exception as exc:
            logger.error(f"MoviePy assembly error: {exc}")
            return None

    def _try_simple(
        self,
        sequence: list[dict],
        resolution: tuple[int, int],
        output_dir: Path,
        cb: Callable,
    ) -> Optional[str]:
        try:
            import sys
            sys.path.insert(0, str(config_manager.config.app_dir))
            from utils.video.simple_assembly import simple_assemble_video

            result = simple_assemble_video(
                sequence=sequence,
                output_path=None,
                target_resolution=resolution,
                progress_callback=cb,
            )
            if isinstance(result, dict) and result.get("status") == "success":
                return result.get("output_path")
            return None
        except Exception as exc:
            logger.error(f"Simple assembly error: {exc}")
            return None


video_assembly_service = VideoAssemblyService()
