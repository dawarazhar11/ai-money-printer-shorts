from typing import Dict, List, Optional

LLM_PRESETS: Dict[str, Dict] = {
    "ollama_mistral": {
        "provider": "ollama",
        "model": "mistral",
        "temperature": 0.7,
        "max_tokens": 2048,
    },
    "ollama_llama3": {
        "provider": "ollama",
        "model": "llama3",
        "temperature": 0.7,
        "max_tokens": 2048,
    },
}

EDGE_TTS_VOICES: Dict[str, Dict] = {
    "en-US-AriaNeural": {"locale": "en-US", "gender": "Female", "name": "Aria"},
    "en-US-GuyNeural": {"locale": "en-US", "gender": "Male", "name": "Guy"},
    "en-GB-SoniaNeural": {"locale": "en-GB", "gender": "Female", "name": "Sonia"},
    "en-AU-NatashaNeural": {"locale": "en-AU", "gender": "Female", "name": "Natasha"},
}


def get_preset(name: str) -> Optional[Dict]:
    return LLM_PRESETS.get(name)


def list_voices_by_locale(locale: str) -> List[str]:
    return [k for k, v in EDGE_TTS_VOICES.items() if v["locale"].startswith(locale)]
