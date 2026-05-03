"""Reference catalogs: LLM presets, TTS voices, etc.

Exposed so the Settings UI can drop in a quick-select picker without
hard-coding choices in the page.
"""

from .llm_presets import LLM_PRESETS, find_preset_by_base_url_and_model, get_preset, get_preset_names
from .tts_voices import EDGE_TTS_VOICES, get_voice, list_voices_by_locale, speed_to_rate

__all__ = [
    "LLM_PRESETS",
    "find_preset_by_base_url_and_model",
    "get_preset",
    "get_preset_names",
    "EDGE_TTS_VOICES",
    "get_voice",
    "list_voices_by_locale",
    "speed_to_rate",
]
