"""OpenAI-compatible LLM provider presets.

Adapted from Pixelle-Video's pixelle_video/llm_presets.py (Apache 2.0).
Every entry below works through the OpenAI Python SDK by setting `base_url`
to the listed endpoint — including Ollama (which ignores the api_key but
the SDK still requires one to be set).
"""

from __future__ import annotations

from typing import Optional

LLM_PRESETS: list[dict] = [
    {
        "name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "api_key_url": "https://platform.openai.com/api-keys",
    },
    {
        "name": "Claude",
        "base_url": "https://api.anthropic.com/v1/",
        "model": "claude-sonnet-4-5",
        "api_key_url": "https://console.anthropic.com/settings/keys",
    },
    {
        "name": "DeepSeek",
        "base_url": "https://api.deepseek.com",
        "model": "deepseek-chat",
        "api_key_url": "https://platform.deepseek.com/api_keys",
    },
    {
        "name": "Qwen",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-max",
        "api_key_url": "https://bailian.console.aliyun.com/?tab=model#/api-key",
    },
    {
        "name": "Moonshot",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "api_key_url": "https://platform.moonshot.cn/console/api-keys",
    },
    {
        "name": "Ollama (local, free)",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3.2",
        "api_key_url": "https://ollama.com/download",
        "default_api_key": "ollama",
    },
    {
        "name": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "llama-3.3-70b-versatile",
        "api_key_url": "https://console.groq.com/keys",
    },
    {
        "name": "Together AI",
        "base_url": "https://api.together.xyz/v1",
        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "api_key_url": "https://api.together.xyz/settings/api-keys",
    },
]


def get_preset_names() -> list[str]:
    return [p["name"] for p in LLM_PRESETS]


def get_preset(name: str) -> dict:
    return next((p for p in LLM_PRESETS if p["name"] == name), {})


def find_preset_by_base_url_and_model(base_url: str, model: str) -> Optional[str]:
    for p in LLM_PRESETS:
        if p["base_url"] == base_url and p["model"] == model:
            return p["name"]
    return None
