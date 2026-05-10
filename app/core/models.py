"""Domain models for ReelForge."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class SegmentType(str, Enum):
    AROLL = "A-Roll"
    BROLL = "B-Roll"


class MediaAsset(BaseModel):
    file_path: str
    mime_type: str = "video/mp4"
    duration_seconds: Optional[float] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def exists(self) -> bool:
        return Path(self.file_path).exists()


class Segment(BaseModel):
    id: str = Field(default_factory=lambda: f"segment_{uuid4().hex[:8]}")
    type: SegmentType = SegmentType.AROLL
    content: str = ""
    broll_prompt: Optional[str] = None
    aroll_asset: Optional[MediaAsset] = None
    broll_asset: Optional[MediaAsset] = None
    heygen_video_id: Optional[str] = None
    status: str = "pending"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ReelProject(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    name: str = "untitled"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    segments: list[Segment] = Field(default_factory=list)
    output_video: Optional[MediaAsset] = None
    captioned_video: Optional[MediaAsset] = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = datetime.utcnow()


class ProgressEvent(BaseModel):
    step: str
    progress: float  # 0.0 – 1.0
    message: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
