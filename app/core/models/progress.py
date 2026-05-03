"""Structured progress events streamed from pipelines to the UI.

Adapted from Pixelle-Video's pixelle_video/models/progress.py (Apache 2.0).
Adds `phase` to make the 8-step ReelForge pipeline observable end to end.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional

Phase = Literal[
    "settings",
    "blueprint",
    "script_segmentation",
    "broll_prompts",
    "a_roll_production",
    "b_roll_production",
    "assembly",
    "captioning",
    "publishing",
]

Action = Literal["audio", "image", "video", "compose", "upload", "transcribe"]


@dataclass
class ProgressEvent:
    """Streamable progress event.

    `progress` is normalized 0.0–1.0 within the *current phase*. Pipelines
    that span multiple phases should emit a fresh event per phase.
    """

    event_type: str
    progress: float
    phase: Optional[Phase] = None
    segment_index: Optional[int] = None
    segment_total: Optional[int] = None
    action: Optional[Action] = None
    message: Optional[str] = None
    extra: Optional[dict] = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.progress <= 1.0:
            raise ValueError(f"progress out of range: {self.progress}")
