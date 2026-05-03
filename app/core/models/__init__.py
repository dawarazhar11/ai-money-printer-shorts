"""Domain models for ReelForge.

Adapted from Pixelle-Video's pixelle_video.models (Apache 2.0). The key
extension is `Segment.kind`: every ReelForge segment is either A-Roll
(narration / talking head) or B-Roll (cutaway visual). Pixelle didn't make
this distinction.
"""

from .media import MediaAsset, MediaResult
from .progress import ProgressEvent
from .project import (
    GenerationResult,
    ProjectConfig,
    ProjectStatus,
    ReelProject,
    Segment,
    SegmentKind,
    SegmentStatus,
)

__all__ = [
    "GenerationResult",
    "MediaAsset",
    "MediaResult",
    "ProgressEvent",
    "ProjectConfig",
    "ProjectStatus",
    "ReelProject",
    "Segment",
    "SegmentKind",
    "SegmentStatus",
]
