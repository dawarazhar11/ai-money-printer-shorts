"""Edge-TTS voice catalogue."""
from __future__ import annotations

EDGE_TTS_VOICES: dict[str, dict] = {
    "en-US-AriaNeural": {"locale": "en-US", "gender": "Female", "style": "newscast"},
    "en-US-GuyNeural": {"locale": "en-US", "gender": "Male", "style": "newscast"},
    "en-US-JennyNeural": {"locale": "en-US", "gender": "Female", "style": "general"},
    "en-US-DavisNeural": {"locale": "en-US", "gender": "Male", "style": "general"},
    "en-GB-SoniaNeural": {"locale": "en-GB", "gender": "Female", "style": "general"},
    "en-GB-RyanNeural": {"locale": "en-GB", "gender": "Male", "style": "general"},
    "en-AU-NatashaNeural": {"locale": "en-AU", "gender": "Female", "style": "general"},
    "en-AU-WilliamNeural": {"locale": "en-AU", "gender": "Male", "style": "general"},
}

DEFAULT_VOICE = "en-US-AriaNeural"


def list_voices_by_locale(locale: str | None = None) -> list[str]:
    if locale is None:
        return list(EDGE_TTS_VOICES.keys())
    return [k for k, v in EDGE_TTS_VOICES.items() if v["locale"].startswith(locale)]
