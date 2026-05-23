"""Tests for app/core/catalogs/* — pure-function lookups, no I/O."""

from __future__ import annotations

import pytest

from core.catalogs.llm_presets import (
    LLM_PRESETS,
    find_preset_by_base_url_and_model,
    get_preset,
    get_preset_names,
)
from core.catalogs.tts_voices import (
    EDGE_TTS_VOICES,
    get_voice,
    list_voices_by_locale,
    speed_to_rate,
)


# ─── LLM presets ───────────────────────────────────────────────────────────


def test_llm_presets_are_non_empty_and_well_formed():
    assert len(LLM_PRESETS) >= 5
    for preset in LLM_PRESETS:
        assert preset["name"]
        assert preset["base_url"].startswith("http")
        assert preset["model"]


def test_get_preset_names_returns_all_names():
    names = get_preset_names()
    assert len(names) == len(LLM_PRESETS)
    assert "OpenAI" in names
    assert "Ollama (local, free)" in names


def test_get_preset_returns_match_or_empty():
    openai = get_preset("OpenAI")
    assert openai["base_url"] == "https://api.openai.com/v1"
    assert get_preset("Nonexistent") == {}


def test_find_preset_by_base_url_and_model_roundtrip():
    for preset in LLM_PRESETS:
        found = find_preset_by_base_url_and_model(preset["base_url"], preset["model"])
        assert found == preset["name"]


def test_find_preset_returns_none_on_no_match():
    assert find_preset_by_base_url_and_model("https://example.invalid", "fake") is None


# ─── Edge-TTS voices ───────────────────────────────────────────────────────


def test_tts_voices_have_english_default():
    voice_ids = [v["id"] for v in EDGE_TTS_VOICES]
    assert "en-US-AriaNeural" in voice_ids


def test_get_voice_returns_full_record():
    voice = get_voice("en-US-AriaNeural")
    assert voice is not None
    assert voice["locale"] == "en-US"
    assert voice["gender"] == "female"
    assert get_voice("nonexistent") is None


def test_list_voices_by_locale_filters_correctly():
    en_us = list_voices_by_locale("en-US")
    assert len(en_us) >= 4
    assert all(v["locale"] == "en-US" for v in en_us)
    assert list_voices_by_locale("xx-XX") == []


# ─── speed_to_rate (regression for float-arithmetic bug) ───────────────────


@pytest.mark.parametrize(
    "speed,expected",
    [
        (1.0, "+0%"),
        (1.2, "+20%"),   # the bug fix: must round, not truncate (was returning +19%)
        (1.5, "+50%"),
        (2.0, "+100%"),
        (0.8, "-20%"),
        (0.5, "-50%"),
        (0.9, "-10%"),
    ],
)
def test_speed_to_rate_rounds_correctly(speed: float, expected: str):
    assert speed_to_rate(speed) == expected
