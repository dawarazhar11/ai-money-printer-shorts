"""ReelProject domain model.

A ReelProject is the unit users work with: name, settings, A-Roll/B-Roll
segments, generated media, captions, and final output. Adapted from
Pixelle-Video's Storyboard / StoryboardFrame / VideoGenerationResult
(Apache 2.0), with the A-Roll/B-Roll distinction that is central to ReelForge.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from .media import MediaAsset

SegmentKind = Literal["a_roll", "b_roll"]
SegmentStatus = Literal["pending", "queued", "generating", "ready", "failed"]
ProjectStatus = Literal["draft", "in_progress", "completed", "failed", "archived"]


class Segment(BaseModel):
    """A single segment of the final video.

    A-Roll segments carry narration text → produce a talking-head clip
    (HeyGen avatar or TTS-only audio over a static frame).
    B-Roll segments carry an image/video prompt → produce a cutaway visual.
    """

    index: int
    kind: SegmentKind
    text: str = Field(default="", description="Narration (A-Roll) or visual description (B-Roll)")
    image_prompt: Optional[str] = Field(default=None, description="Optimized image-gen prompt (B-Roll)")
    duration: float = Field(default=0.0, description="Final clip duration in seconds")
    status: SegmentStatus = Field(default="pending")

    # Generated assets
    audio: Optional[MediaAsset] = None
    visual: Optional[MediaAsset] = None
    composed: Optional[MediaAsset] = None

    # Trace / debug
    backend: Optional[str] = Field(default=None, description="Which generator produced `visual`")
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    def is_ready(self) -> bool:
        return self.status == "ready" and self.composed is not None


class ProjectConfig(BaseModel):
    """Per-project rendering / generation parameters."""

    width: int = 1080
    height: int = 1920
    fps: int = 30
    target_duration: float = Field(default=60.0, description="Target total length in seconds")

    # Backend choices
    a_roll_backend: Literal["heygen", "edge_tts", "comfyui_tts"] = "edge_tts"
    b_roll_backend: Literal["comfyui", "replicate", "playwright"] = "comfyui"

    # ComfyUI workflow paths (relative to workflows/)
    image_workflow: Optional[str] = None
    video_workflow: Optional[str] = None
    tts_workflow: Optional[str] = None

    # HeyGen overrides (fall back to global config if None)
    heygen_avatar_id: Optional[str] = None
    heygen_voice_id: Optional[str] = None

    # Caption / styling
    caption_effect: Literal["fade", "scale", "combined", "none"] = "combined"
    frame_template: str = "1080x1920/default.html"

    # Audio
    bgm_path: Optional[str] = Field(default=None, description="Path to background music")
    bgm_volume: float = Field(default=0.15, ge=0.0, le=1.0)


class ReelProject(BaseModel):
    """Top-level project the user works with."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    name: str
    status: ProjectStatus = Field(default="draft")
    config: ProjectConfig = Field(default_factory=ProjectConfig)

    # Workflow content
    raw_script: str = Field(default="")
    segments: list[Segment] = Field(default_factory=list)

    # Final output
    final_video: Optional[MediaAsset] = None
    captioned_video: Optional[MediaAsset] = None
    thumbnail: Optional[MediaAsset] = None

    # Publishing trace
    published_to: dict[str, str] = Field(
        default_factory=dict,
        description="platform → URL or post id, e.g. {'youtube': 'https://...'}",
    )

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # ── derived / helper properties ────────────────────────────────────────

    @property
    def a_roll(self) -> list[Segment]:
        return [s for s in self.segments if s.kind == "a_roll"]

    @property
    def b_roll(self) -> list[Segment]:
        return [s for s in self.segments if s.kind == "b_roll"]

    @property
    def progress(self) -> float:
        if not self.segments:
            return 0.0
        ready = sum(1 for s in self.segments if s.is_ready())
        return ready / len(self.segments)

    @property
    def total_duration(self) -> float:
        return sum(s.duration for s in self.segments)

    @property
    def is_complete(self) -> bool:
        return all(s.is_ready() for s in self.segments) and self.final_video is not None

    def touch(self) -> None:
        self.updated_at = datetime.now()


class GenerationResult(BaseModel):
    """Final pipeline output."""

    project_id: str
    video_path: str
    duration: float
    file_size: int
    created_at: datetime = Field(default_factory=datetime.now)
