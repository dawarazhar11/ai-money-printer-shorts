"""Static catalogs for LLM presets, voices, etc."""
from .voices import EDGE_TTS_VOICES, list_voices_by_locale
from .presets import LLM_PRESETS, get_preset

__all__ = ["EDGE_TTS_VOICES", "list_voices_by_locale", "LLM_PRESETS", "get_preset"]
