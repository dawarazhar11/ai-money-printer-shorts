"""LLM preset catalogue."""
from __future__ import annotations

LLM_PRESETS: dict[str, dict] = {
    "fast": {"model": "llama3.2:3b", "temperature": 0.7, "max_tokens": 1024},
    "balanced": {"model": "llama3.1:8b", "temperature": 0.6, "max_tokens": 2048},
    "quality": {"model": "llama3.1:70b", "temperature": 0.5, "max_tokens": 4096},
}


def get_preset(name: str) -> dict:
    return LLM_PRESETS.get(name, LLM_PRESETS["balanced"])
