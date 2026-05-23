"""Tests for app/core/config/loader.py — YAML load + .env overlay."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from core.config.loader import _coerce, _set_dotted, load_config_dict, save_config_dict


# ─── _coerce ───────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected,expected_type",
    [
        ("42", 42, int),
        ("0", 0, int),
        ("3.14", 3.14, float),
        ("hello", "hello", str),
        ("https://api.example.com/v1", "https://api.example.com/v1", str),
        ("", "", str),
    ],
)
def test_coerce_types(raw, expected, expected_type):
    result = _coerce(raw)
    assert result == expected
    assert type(result) is expected_type


# ─── _set_dotted ───────────────────────────────────────────────────────────


def test_set_dotted_creates_nested_path():
    data: dict = {}
    _set_dotted(data, "a.b.c", 42)
    assert data == {"a": {"b": {"c": 42}}}


def test_set_dotted_overwrites_leaf():
    data = {"a": {"b": "old"}}
    _set_dotted(data, "a.b", "new")
    assert data == {"a": {"b": "new"}}


def test_set_dotted_replaces_non_dict_intermediate():
    data = {"a": "not a dict"}
    _set_dotted(data, "a.b", 1)
    assert data == {"a": {"b": 1}}


# ─── load_config_dict + env overlay ────────────────────────────────────────


def test_load_returns_empty_dict_when_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # Strip env vars so overlay doesn't inject anything
    for env_name in (
        "HEYGEN_API_KEY", "OPENAI_API_KEY", "OPENAI_MODEL", "OPENAI_BASE_URL",
        "REPLICATE_API_TOKEN", "RUNNINGHUB_API_KEY", "COMFYUI_WS_PORT",
        "COMFYUI_IMAGE_API_URL", "COMFYUI_VIDEO_API_URL", "OLLAMA_API_URL", "OLLAMA_MODEL",
    ):
        monkeypatch.delenv(env_name, raising=False)
    result = load_config_dict(str(tmp_path / "missing.yaml"))
    assert result == {}


def test_load_returns_yaml_contents(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"project_name": "test", "llm": {"model": "gpt-4"}}))
    # Don't let env vars pollute the assertion
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    result = load_config_dict(str(cfg))
    assert result["project_name"] == "test"
    assert result["llm"]["model"] == "gpt-4"


def test_env_overlay_injects_heygen_api_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HEYGEN_API_KEY", "secret-key")
    result = load_config_dict(str(tmp_path / "nope.yaml"))
    assert result["heygen"]["api_key"] == "secret-key"


def test_env_overlay_coerces_port_to_int(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("COMFYUI_WS_PORT", "9999")
    result = load_config_dict(str(tmp_path / "nope.yaml"))
    assert result["comfyui"]["ws_port"] == 9999
    assert type(result["comfyui"]["ws_port"]) is int


def test_env_overlay_overrides_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"llm": {"model": "yaml-model"}}))
    monkeypatch.setenv("OPENAI_MODEL", "env-model")

    result = load_config_dict(str(cfg))
    assert result["llm"]["model"] == "env-model"


def test_env_overlay_skips_empty_strings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(yaml.dump({"llm": {"api_key": "yaml-key"}}))
    monkeypatch.setenv("OPENAI_API_KEY", "")  # empty string must NOT clobber yaml

    result = load_config_dict(str(cfg))
    assert result["llm"]["api_key"] == "yaml-key"


# ─── save_config_dict ──────────────────────────────────────────────────────


def test_save_roundtrips_via_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    cfg_path = tmp_path / "out.yaml"
    payload = {"project_name": "rt", "llm": {"model": "gpt-4o", "api_key": "k"}}
    save_config_dict(payload, str(cfg_path))

    # Clear env so load returns just what's on disk
    for env_name in ("OPENAI_API_KEY", "OPENAI_MODEL"):
        monkeypatch.delenv(env_name, raising=False)
    loaded = load_config_dict(str(cfg_path))
    assert loaded["project_name"] == "rt"
    assert loaded["llm"]["model"] == "gpt-4o"
    assert loaded["llm"]["api_key"] == "k"
