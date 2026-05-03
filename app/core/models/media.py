"""Media generation results.

Adapted from Pixelle-Video's pixelle_video/models/media.py (Apache 2.0).
`MediaAsset` is the persisted, on-disk form; `MediaResult` is the transient
return value from a generator (URL or temp path) before it has been stored.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field

MediaType = Literal["image", "video", "audio"]
Backend = Literal["comfyui", "runninghub", "replicate", "heygen", "edge_tts", "playwright", "user_upload"]


class MediaResult(BaseModel):
    """Return value from a generator before it has been persisted."""

    media_type: MediaType
    url: str = Field(description="Remote URL or local temp path")
    duration: Optional[float] = Field(default=None, description="Seconds (video/audio only)")
    width: Optional[int] = None
    height: Optional[int] = None

    @property
    def is_image(self) -> bool:
        return self.media_type == "image"

    @property
    def is_video(self) -> bool:
        return self.media_type == "video"

    @property
    def is_audio(self) -> bool:
        return self.media_type == "audio"


class MediaAsset(BaseModel):
    """Persisted media asset on disk."""

    media_type: MediaType
    backend: Backend
    path: Path
    duration: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)

    def exists(self) -> bool:
        return self.path.exists()

    @property
    def size_bytes(self) -> int:
        return self.path.stat().st_size if self.exists() else 0
