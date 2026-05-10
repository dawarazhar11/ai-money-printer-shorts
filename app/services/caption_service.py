"""Caption service — registry pattern over typography_effects modules."""
from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any, Callable, Optional

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.caption")

# ---------------------------------------------------------------------------
# Registry of typography effect modules
# Each entry maps a style-key to the module dotted-path and the render fn name.
# ---------------------------------------------------------------------------
_EFFECT_REGISTRY: dict[str, dict[str, str]] = {
    "fade": {
        "module": "app.utils.video.typography_effects_fade",
        "render_fn": "render_text_with_fade_effect",
    },
    "scale": {
        "module": "app.utils.video.typography_effects_scale",
        "render_fn": "render_text_with_scale_effect",
    },
    "combined": {
        "module": "app.utils.video.typography_effects_combined",
        "render_fn": "render_text_with_combined_effects",
    },
}


def list_effects() -> list[str]:
    return list(_EFFECT_REGISTRY.keys())


def get_effect_fn(effect_key: str) -> Optional[Callable]:
    """Import and return the render function for *effect_key*, or None if unavailable."""
    spec = _EFFECT_REGISTRY.get(effect_key)
    if spec is None:
        logger.warning(f"Unknown typography effect: {effect_key}")
        return None
    try:
        mod = importlib.import_module(spec["module"])
        return getattr(mod, spec["render_fn"])
    except (ImportError, AttributeError) as exc:
        logger.warning(f"Could not load effect {effect_key}: {exc}")
        return None


class CaptionService:
    """Orchestrate transcription → caption overlay → export."""

    def add_captions(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        style_name: str = "tiktok",
        animation_style: str = "word_by_word",
        model_size: str = "base",
        transcription_engine: str = "auto",
        font_size: int = 50,
        extra_params: Optional[dict[str, Any]] = None,
        progress_cb: Optional[Callable[[float, str], None]] = None,
    ) -> MediaAsset:
        """Add animated captions to *video_path* and return the output MediaAsset."""
        import sys
        sys.path.insert(0, str(config_manager.config.app_dir))

        from app.utils.video.captions import add_captions_to_video

        if output_path is None:
            stem = Path(video_path).stem
            output_path = str(Path(video_path).parent / f"{stem}_captioned.mp4")

        effect_params = extra_params or {}
        if font_size:
            effect_params["font_size"] = font_size

        logger.info(f"Adding captions: style={style_name} animation={animation_style} engine={transcription_engine}")

        result = add_captions_to_video(
            video_path=video_path,
            output_path=output_path,
            style_name=style_name,
            model_size=model_size,
            transcription_engine=transcription_engine,
            animation_style=animation_style,
            effect_params=effect_params,
            progress_callback=progress_cb,
        )

        if isinstance(result, dict):
            if result.get("status") != "success":
                raise RuntimeError(f"Caption generation failed: {result.get('message')}")
            out = result.get("output_path", output_path)
        else:
            out = str(result) if result else output_path

        logger.info(f"Captions done → {out}")
        return MediaAsset(file_path=out, mime_type="video/mp4")


caption_service = CaptionService()
