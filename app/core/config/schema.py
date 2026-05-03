"""ReelForge configuration schema (Pydantic).

Single source of truth for all configuration defaults and validation. Adapted
from Pixelle-Video's pixelle_video/config/schema.py (Apache 2.0) and extended
with ReelForge-specific subsystems.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


# ─── LLM ────────────────────────────────────────────────────────────────────


class LLMConfig(BaseModel):
    """OpenAI-compatible LLM (used for narration / prompt generation).

    Supports any provider that exposes an OpenAI-compatible endpoint:
    OpenAI, Qwen, DeepSeek, Anthropic (via proxy), Moonshot, Ollama, etc.
    """

    api_key: str = Field(default="", description="LLM API key")
    base_url: str = Field(default="", description="OpenAI-compatible base URL")
    model: str = Field(default="", description="Model name")


class OllamaConfig(BaseModel):
    """Local Ollama for free LLM inference (script segmentation, B-Roll prompts)."""

    api_url: str = Field(default="http://127.0.0.1:11434/api", description="Ollama API endpoint")
    model: str = Field(default="llama3", description="Default Ollama model")


# ─── TTS ────────────────────────────────────────────────────────────────────


class TTSLocalConfig(BaseModel):
    """Edge-TTS settings (free, no API key)."""

    voice: str = Field(default="en-US-AriaNeural", description="Edge-TTS voice ID")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed multiplier")


class TTSComfyUIConfig(BaseModel):
    """ComfyUI-based TTS (Index-TTS, ChatTTS, etc.)."""

    default_workflow: Optional[str] = Field(default=None)


class TTSConfig(BaseModel):
    inference_mode: Literal["local", "comfyui", "heygen"] = Field(
        default="local",
        description="local=Edge-TTS, comfyui=workflow, heygen=avatar voice (A-Roll)",
    )
    local: TTSLocalConfig = Field(default_factory=TTSLocalConfig)
    comfyui: TTSComfyUIConfig = Field(default_factory=TTSComfyUIConfig)


# ─── ComfyUI / RunningHub ───────────────────────────────────────────────────


class ImageSubConfig(BaseModel):
    default_workflow: Optional[str] = Field(default=None)
    prompt_prefix: str = Field(default="", description="Prefix prepended to every B-Roll image prompt")


class VideoSubConfig(BaseModel):
    default_workflow: Optional[str] = Field(default=None)
    prompt_prefix: str = Field(default="", description="Prefix prepended to every B-Roll video prompt")


class ComfyUIConfig(BaseModel):
    image_api_url: str = Field(default="http://127.0.0.1:8000", description="ComfyUI image server")
    video_api_url: str = Field(default="http://127.0.0.1:8001", description="ComfyUI video server")
    ws_host: str = Field(default="127.0.0.1", description="WebSocket host for progress")
    ws_port: int = Field(default=8000, description="WebSocket port for progress")
    api_key: Optional[str] = Field(default=None, description="ComfyUI API key (optional)")
    runninghub_api_key: Optional[str] = Field(default=None, description="RunningHub cloud API key")
    runninghub_concurrent_limit: int = Field(default=1, ge=1, le=10)
    runninghub_instance_type: Optional[str] = Field(
        default=None, description="'plus' for 48GB VRAM, None for default"
    )
    image: ImageSubConfig = Field(default_factory=ImageSubConfig)
    video: VideoSubConfig = Field(default_factory=VideoSubConfig)


# ─── HeyGen (avatar A-Roll) ─────────────────────────────────────────────────


class HeyGenConfig(BaseModel):
    """HeyGen avatar video API (A-Roll talking-head segments)."""

    api_key: str = Field(default="")
    default_avatar_id: str = Field(default="", description="Avatar pose ID")
    default_voice_id: str = Field(default="", description="Voice ID")
    background_color: str = Field(default="#008000", description="Chroma-key background")


# ─── Replicate (cloud B-Roll) ───────────────────────────────────────────────


class ReplicateConfig(BaseModel):
    api_token: str = Field(default="")
    default_image_model: str = Field(
        default="stability-ai/sdxl",
        description="Replicate model slug for image generation",
    )
    default_video_model: str = Field(
        default="wavespeedai/wan-2.1-t2v-480p",
        description="Replicate model slug for video generation",
    )


# ─── Publishing (YouTube / TikTok / Instagram) ──────────────────────────────


class YouTubeConfig(BaseModel):
    client_secret_path: str = Field(default="config/client_secret.json")
    token_cache_path: str = Field(default="config/youtube_token.json")
    default_privacy: Literal["private", "unlisted", "public"] = Field(default="private")


class TikTokConfig(BaseModel):
    client_key: str = Field(default="")
    client_secret: str = Field(default="")
    redirect_uri: str = Field(default="http://localhost:8080/tiktok/callback")


class InstagramConfig(BaseModel):
    """Meta Graph API (Instagram Business / Creator account)."""

    access_token: str = Field(default="")
    business_account_id: str = Field(default="")


class PublishingConfig(BaseModel):
    youtube: YouTubeConfig = Field(default_factory=YouTubeConfig)
    tiktok: TikTokConfig = Field(default_factory=TikTokConfig)
    instagram: InstagramConfig = Field(default_factory=InstagramConfig)


# ─── Templates ──────────────────────────────────────────────────────────────


class TemplateConfig(BaseModel):
    """HTML→video frame templates (ported from Pixelle)."""

    default_template: str = Field(default="1080x1920/default.html")
    templates_dir: str = Field(default="app/templates")


# ─── Storage ────────────────────────────────────────────────────────────────


class StorageConfig(BaseModel):
    output_dir: str = Field(default="output", description="Where finished videos land")
    media_dir: str = Field(default="media", description="Per-asset cache (images/videos/audio)")
    user_data_dir: str = Field(default="app/config/user_data", description="Per-project state")


# ─── Root ───────────────────────────────────────────────────────────────────


class ReelForgeConfig(BaseModel):
    """ReelForge root configuration."""

    project_name: str = Field(default="ReelForge")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    comfyui: ComfyUIConfig = Field(default_factory=ComfyUIConfig)
    heygen: HeyGenConfig = Field(default_factory=HeyGenConfig)
    replicate: ReplicateConfig = Field(default_factory=ReplicateConfig)
    publishing: PublishingConfig = Field(default_factory=PublishingConfig)
    template: TemplateConfig = Field(default_factory=TemplateConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    # ── Validation helpers ──────────────────────────────────────────────────

    def is_llm_configured(self) -> bool:
        return bool(self.llm.api_key.strip() and self.llm.base_url.strip() and self.llm.model.strip())

    def is_ollama_configured(self) -> bool:
        return bool(self.ollama.api_url.strip() and self.ollama.model.strip())

    def is_heygen_configured(self) -> bool:
        return bool(self.heygen.api_key.strip())

    def is_replicate_configured(self) -> bool:
        return bool(self.replicate.api_token.strip())

    def has_image_backend(self) -> bool:
        return bool(self.comfyui.image_api_url.strip()) or self.is_replicate_configured()

    def has_a_roll_backend(self) -> bool:
        """A-Roll requires either HeyGen (avatar) or local TTS (synth voice)."""
        return self.is_heygen_configured() or self.tts.inference_mode == "local"

    def validate_required(self) -> tuple[bool, list[str]]:
        """Return (ok, missing) so the UI can show actionable errors."""
        missing: list[str] = []
        if not (self.is_llm_configured() or self.is_ollama_configured()):
            missing.append("LLM or Ollama (script segmentation needs at least one)")
        if not self.has_a_roll_backend():
            missing.append("A-Roll backend (HeyGen or local TTS)")
        if not self.has_image_backend():
            missing.append("B-Roll backend (ComfyUI or Replicate)")
        return (len(missing) == 0, missing)

    def to_dict(self) -> dict:
        return self.model_dump()
