from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List, Dict, Any


@dataclass
class MediaAsset:
    path: str
    asset_type: str = "video"
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def exists(self) -> bool:
        return Path(self.path).exists()


@dataclass
class Segment:
    id: str
    type: str  # "A-Roll" or "B-Roll"
    content: str = ""
    media_asset: Optional[MediaAsset] = None
    status: str = "not_started"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReelProject:
    id: str
    name: str
    path: str
    segments: List[Segment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_segment(self, segment_id: str) -> Optional[Segment]:
        return next((s for s in self.segments if s.id == segment_id), None)


@dataclass
class ProgressEvent:
    event_type: str  # "progress", "complete", "error"
    progress: Optional[float] = None  # 0.0-1.0
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
