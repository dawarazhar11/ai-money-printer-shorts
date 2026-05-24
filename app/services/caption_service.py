import sys
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.caption_service")

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

try:
    from utils.video.captions import add_captions_to_video, get_available_caption_styles, CAPTION_STYLES
    _CAPTIONS_AVAILABLE = True
except ImportError:
    _CAPTIONS_AVAILABLE = False
    logger.warning("utils.video.captions not importable")

try:
    from utils.audio.transcription import transcribe_video
    _TRANSCRIPTION_AVAILABLE = True
except ImportError:
    _TRANSCRIPTION_AVAILABLE = False
    logger.warning("utils.audio.transcription not importable")


# --- Typography effect registry (Pixelle pipeline registry pattern) ---
_TYPOGRAPHY_REGISTRY: Dict[str, Callable] = {}


def register_typography_effect(name: str, fn: Callable) -> None:
    _TYPOGRAPHY_REGISTRY[name] = fn


def list_typography_effects() -> list:
    return list(_TYPOGRAPHY_REGISTRY.keys())


def _load_builtin_effects() -> None:
    try:
        from utils.video.typography_effects_fade import apply_fade_effect
        register_typography_effect("fade", apply_fade_effect)
    except (ImportError, Exception):
        pass
    try:
        from utils.video.typography_effects_scale import apply_scale_effect
        register_typography_effect("scale", apply_scale_effect)
    except (ImportError, Exception):
        pass
    # typography_effects_combined calls sys.exit(1) on import failure — skip silently
    try:
        import importlib
        mod = importlib.import_module("utils.video.typography_effects_combined")
        fn = getattr(mod, "render_word_with_combined_effects", None)
        if fn:
            register_typography_effect("combined", fn)
    except (ImportError, SystemExit, Exception):
        pass


_load_builtin_effects()


class CaptionService:
    def transcribe(self, video_path: str, engine: str = "whisper", model_size: str = "base") -> dict:
        if not _TRANSCRIPTION_AVAILABLE:
            raise RuntimeError("Transcription dependencies not installed")
        logger.info("Transcribing: %s (engine=%s model=%s)", video_path, engine, model_size)
        return transcribe_video(video_path, engine=engine, model_size=model_size)

    def apply_captions(
        self,
        video_path: str,
        output_path: str,
        style: str = "tiktok",
        animation_style: str = "word_by_word",
        transcription: Optional[dict] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> MediaAsset:
        if not _CAPTIONS_AVAILABLE:
            raise RuntimeError("Caption dependencies not installed")
        params = params or {}
        logger.info("Applying captions: %s style=%s anim=%s -> %s",
                    video_path, style, animation_style, output_path)

        effect_fn = _TYPOGRAPHY_REGISTRY.get(animation_style)
        result = add_captions_to_video(
            video_path=video_path,
            output_path=output_path,
            style=style,
            animation_style=animation_style,
            transcription=transcription,
            typography_effect=effect_fn,
            **params,
        )
        if isinstance(result, dict) and result.get("status") == "error":
            raise RuntimeError(result.get("message", "Caption failed"))
        return MediaAsset(path=output_path, asset_type="video")

    def list_styles(self) -> list:
        if not _CAPTIONS_AVAILABLE:
            return []
        return get_available_caption_styles()

    def list_animation_styles(self) -> list:
        built_in = ["word_by_word", "fade_in_out", "scale_pulse", "color_highlight", "single_word_focus"]
        registry_styles = list_typography_effects()
        return sorted(set(built_in + registry_styles))


caption_service = CaptionService()
