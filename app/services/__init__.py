"""Service layer.

Each service wraps one external system (TTS, LLM, ComfyUI, Replicate, HeyGen,
Playwright, transcription) behind a small, retried, validated interface.
Pages should call services, never the underlying SDK directly.
"""
