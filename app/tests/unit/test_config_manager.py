"""Tests for app/core/config/manager.py — round-trip + deep merge."""

from __future__ import annotations

from pathlib import Path

import yaml


# ─── Basic lifecycle ───────────────────────────────────────────────────────


def test_loads_defaults_when_no_file(isolated_config):
    cfg = isolated_config.config
    assert cfg.project_name == "ReelForge"
    assert cfg.llm.api_key == ""
    assert cfg.tts.inference_mode == "local"


def test_save_creates_yaml(isolated_config, tmp_path: Path):
    isolated_config.save()
    cfg_path = Path(isolated_config.config_path)
    assert cfg_path.exists()
    data = yaml.safe_load(cfg_path.read_text())
    assert data["project_name"] == "ReelForge"


# ─── Deep merge semantics ──────────────────────────────────────────────────


def test_update_deep_merges_siblings(isolated_config):
    isolated_config.update({"llm": {"model": "gpt-4"}})
    assert isolated_config.config.llm.model == "gpt-4"
    # Other LLM fields preserved at defaults
    assert isolated_config.config.llm.api_key == ""
    assert isolated_config.config.llm.base_url == ""

    # Updating a different subsystem must NOT wipe llm
    isolated_config.update({"heygen": {"api_key": "hg-key"}})
    assert isolated_config.config.llm.model == "gpt-4"
    assert isolated_config.config.heygen.api_key == "hg-key"


def test_update_overrides_nested_fields(isolated_config):
    isolated_config.update({"tts": {"local": {"voice": "en-GB-RyanNeural", "speed": 1.5}}})
    assert isolated_config.config.tts.local.voice == "en-GB-RyanNeural"
    assert isolated_config.config.tts.local.speed == 1.5
    # inference_mode at parent level preserved
    assert isolated_config.config.tts.inference_mode == "local"


# ─── Round-trip (the property the Settings page relies on) ─────────────────


def test_round_trip_preserves_updates(isolated_config):
    isolated_config.update(
        {
            "llm": {"api_key": "sk-test", "model": "claude-3", "base_url": "https://x"},
            "heygen": {"api_key": "hg-key", "default_avatar_id": "av-1"},
        }
    )
    isolated_config.save()
    isolated_config.reload()

    assert isolated_config.config.llm.api_key == "sk-test"
    assert isolated_config.config.llm.model == "claude-3"
    assert isolated_config.config.heygen.api_key == "hg-key"
    assert isolated_config.config.heygen.default_avatar_id == "av-1"


# ─── validate_required transitions ─────────────────────────────────────────


def test_validate_required_passes_with_defaults(isolated_config):
    # Schema defaults provide: Ollama url+model (LLM), local TTS (A-Roll),
    # ComfyUI image_api_url (B-Roll). All three required backends satisfied.
    ok, missing = isolated_config.config.validate_required()
    assert ok, f"expected pass but missing: {missing}"


def test_validate_required_fails_when_llm_options_all_blanked(isolated_config):
    isolated_config.update({"ollama": {"api_url": "", "model": ""}})
    # llm.api_key / base_url / model are already empty by default
    ok, missing = isolated_config.config.validate_required()
    assert not ok
    assert any("LLM" in m or "Ollama" in m for m in missing)


def test_validate_required_fails_when_a_roll_broken(isolated_config):
    isolated_config.update({"tts": {"inference_mode": "heygen"}})  # no heygen key
    ok, missing = isolated_config.config.validate_required()
    assert not ok
    assert any("A-Roll" in m for m in missing)


def test_validate_required_fails_when_b_roll_broken(isolated_config):
    isolated_config.update({"comfyui": {"image_api_url": ""}})
    ok, missing = isolated_config.config.validate_required()
    assert not ok
    assert any("B-Roll" in m for m in missing)
