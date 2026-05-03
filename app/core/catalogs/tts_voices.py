"""Edge-TTS voice catalog.

Adapted from Pixelle-Video's pixelle_video/tts_voices.py (Apache 2.0).
The voices below are a curated subset of Microsoft Edge-TTS — call
`edge_tts.list_voices()` if you need the full ~400-entry list.

ReelForge defaults to English (Edge-TTS is the free A-Roll fallback for
English-speaking creators) and includes the most common other locales.
"""

from __future__ import annotations

from typing import Optional

EDGE_TTS_VOICES: list[dict] = [
    # ── English (default focus) ─────────────────────────────────────────
    {"id": "en-US-AriaNeural", "label": "Aria (US, female)", "locale": "en-US", "gender": "female"},
    {"id": "en-US-JennyNeural", "label": "Jenny (US, female)", "locale": "en-US", "gender": "female"},
    {"id": "en-US-GuyNeural", "label": "Guy (US, male)", "locale": "en-US", "gender": "male"},
    {"id": "en-US-DavisNeural", "label": "Davis (US, male)", "locale": "en-US", "gender": "male"},
    {"id": "en-US-EmmaNeural", "label": "Emma (US, female)", "locale": "en-US", "gender": "female"},
    {"id": "en-US-BrianNeural", "label": "Brian (US, male)", "locale": "en-US", "gender": "male"},
    {"id": "en-GB-SoniaNeural", "label": "Sonia (UK, female)", "locale": "en-GB", "gender": "female"},
    {"id": "en-GB-RyanNeural", "label": "Ryan (UK, male)", "locale": "en-GB", "gender": "male"},
    {"id": "en-AU-NatashaNeural", "label": "Natasha (AU, female)", "locale": "en-AU", "gender": "female"},
    {"id": "en-IN-NeerjaNeural", "label": "Neerja (IN, female)", "locale": "en-IN", "gender": "female"},
    # ── Chinese (from Pixelle) ──────────────────────────────────────────
    {"id": "zh-CN-XiaoxiaoNeural", "label": "Xiaoxiao (CN, female)", "locale": "zh-CN", "gender": "female"},
    {"id": "zh-CN-YunjianNeural", "label": "Yunjian (CN, male)", "locale": "zh-CN", "gender": "male"},
    {"id": "zh-CN-YunxiNeural", "label": "Yunxi (CN, male)", "locale": "zh-CN", "gender": "male"},
    {"id": "zh-CN-XiaoyiNeural", "label": "Xiaoyi (CN, female)", "locale": "zh-CN", "gender": "female"},
    # ── European ────────────────────────────────────────────────────────
    {"id": "es-ES-ElviraNeural", "label": "Elvira (ES, female)", "locale": "es-ES", "gender": "female"},
    {"id": "es-ES-AlvaroNeural", "label": "Alvaro (ES, male)", "locale": "es-ES", "gender": "male"},
    {"id": "fr-FR-EloiseNeural", "label": "Eloise (FR, female)", "locale": "fr-FR", "gender": "female"},
    {"id": "fr-FR-HenriNeural", "label": "Henri (FR, male)", "locale": "fr-FR", "gender": "male"},
    {"id": "de-DE-AmalaNeural", "label": "Amala (DE, female)", "locale": "de-DE", "gender": "female"},
    {"id": "de-DE-ConradNeural", "label": "Conrad (DE, male)", "locale": "de-DE", "gender": "male"},
    {"id": "pt-PT-RaquelNeural", "label": "Raquel (PT, female)", "locale": "pt-PT", "gender": "female"},
    {"id": "pt-PT-DuarteNeural", "label": "Duarte (PT, male)", "locale": "pt-PT", "gender": "male"},
    {"id": "ru-RU-SvetlanaNeural", "label": "Svetlana (RU, female)", "locale": "ru-RU", "gender": "female"},
    {"id": "ru-RU-DmitryNeural", "label": "Dmitry (RU, male)", "locale": "ru-RU", "gender": "male"},
    # ── Asian (additional) ──────────────────────────────────────────────
    {"id": "ja-JP-NanamiNeural", "label": "Nanami (JP, female)", "locale": "ja-JP", "gender": "female"},
    {"id": "ja-JP-KeitaNeural", "label": "Keita (JP, male)", "locale": "ja-JP", "gender": "male"},
    {"id": "ko-KR-SunHiNeural", "label": "SunHi (KR, female)", "locale": "ko-KR", "gender": "female"},
    {"id": "ko-KR-InJoonNeural", "label": "InJoon (KR, male)", "locale": "ko-KR", "gender": "male"},
    {"id": "hi-IN-SwaraNeural", "label": "Swara (IN, female)", "locale": "hi-IN", "gender": "female"},
    {"id": "ar-SA-HamedNeural", "label": "Hamed (SA, male)", "locale": "ar-SA", "gender": "male"},
    {"id": "tr-TR-EmelNeural", "label": "Emel (TR, female)", "locale": "tr-TR", "gender": "female"},
    {"id": "tr-TR-AhmetNeural", "label": "Ahmet (TR, male)", "locale": "tr-TR", "gender": "male"},
]


def get_voice(voice_id: str) -> Optional[dict]:
    return next((v for v in EDGE_TTS_VOICES if v["id"] == voice_id), None)


def list_voices_by_locale(locale: str) -> list[dict]:
    return [v for v in EDGE_TTS_VOICES if v["locale"] == locale]


def speed_to_rate(speed: float) -> str:
    """Convert speed multiplier (1.0=normal) → Edge-TTS rate string ('+20%').

    Uses round() so float arithmetic (1.2 - 1.0 = 0.19999…) doesn't shave 1%.
    """
    pct = round((speed - 1.0) * 100)
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct}%"
