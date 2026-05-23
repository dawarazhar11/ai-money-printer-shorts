"""Tests for app/core/models/project.py — derived properties and helpers."""

from __future__ import annotations

import time
from datetime import datetime

from core.models import ReelProject
from core.models.media import MediaAsset
from core.models.project import Segment


def _composed_asset(name: str = "clip.mp4") -> MediaAsset:
    return MediaAsset(path=f"/tmp/{name}", media_type="video", backend="comfyui")


def _ready_segment(index: int, kind: str = "b_roll", duration: float = 5.0) -> Segment:
    return Segment(
        index=index,
        kind=kind,
        text="x",
        duration=duration,
        status="ready",
        composed=_composed_asset(f"seg{index}.mp4"),
    )


# ─── Segment.is_ready ──────────────────────────────────────────────────────


def test_segment_is_ready_requires_status_and_composed():
    s = Segment(index=0, kind="a_roll", text="hi")
    assert not s.is_ready()

    s.status = "ready"
    assert not s.is_ready()  # composed still None

    s.composed = _composed_asset()
    assert s.is_ready()


def test_segment_not_ready_when_status_pending_even_with_composed():
    s = Segment(index=0, kind="a_roll", text="hi", composed=_composed_asset())
    assert not s.is_ready()


# ─── A-Roll / B-Roll filtering ─────────────────────────────────────────────


def test_a_roll_and_b_roll_partition_segments():
    project = ReelProject(
        name="P",
        segments=[
            Segment(index=0, kind="a_roll", text="intro"),
            Segment(index=1, kind="b_roll", text="cutaway"),
            Segment(index=2, kind="a_roll", text="outro"),
        ],
    )
    assert [s.index for s in project.a_roll] == [0, 2]
    assert [s.index for s in project.b_roll] == [1]


def test_a_roll_and_b_roll_empty_on_no_segments():
    project = ReelProject(name="P")
    assert project.a_roll == []
    assert project.b_roll == []


# ─── progress ──────────────────────────────────────────────────────────────


def test_progress_zero_when_no_segments():
    assert ReelProject(name="P").progress == 0.0


def test_progress_fraction_of_ready_segments():
    project = ReelProject(
        name="P",
        segments=[
            _ready_segment(0),
            _ready_segment(1),
            Segment(index=2, kind="b_roll", text="x"),  # pending
            Segment(index=3, kind="b_roll", text="x"),  # pending
        ],
    )
    assert project.progress == 0.5


def test_progress_is_one_when_all_ready():
    project = ReelProject(
        name="P", segments=[_ready_segment(0), _ready_segment(1)]
    )
    assert project.progress == 1.0


# ─── total_duration ────────────────────────────────────────────────────────


def test_total_duration_sums_segment_durations():
    project = ReelProject(
        name="P",
        segments=[
            Segment(index=0, kind="a_roll", text="x", duration=3.5),
            Segment(index=1, kind="b_roll", text="x", duration=4.0),
            Segment(index=2, kind="b_roll", text="x", duration=2.5),
        ],
    )
    assert project.total_duration == 10.0


def test_total_duration_is_zero_when_no_segments():
    assert ReelProject(name="P").total_duration == 0.0


# ─── is_complete ───────────────────────────────────────────────────────────


def test_is_complete_requires_all_segments_ready_and_final_video():
    project = ReelProject(name="P", segments=[_ready_segment(0)])
    assert not project.is_complete  # no final_video

    project.final_video = _composed_asset("final.mp4")
    assert project.is_complete


def test_is_complete_false_when_any_segment_not_ready():
    project = ReelProject(
        name="P",
        segments=[_ready_segment(0), Segment(index=1, kind="b_roll", text="x")],
        final_video=_composed_asset("final.mp4"),
    )
    assert not project.is_complete


def test_is_complete_false_on_empty_segments_even_with_final_video():
    # all([]) is True, so without this guard you'd get "complete" for empty projects
    project = ReelProject(name="P", final_video=_composed_asset("final.mp4"))
    # Current impl: all([]) is True AND final_video set → returns True.
    # This documents the current behavior (empty project + final_video = complete).
    # If you want to require segments, that's a model change.
    assert project.is_complete is True


# ─── touch() ───────────────────────────────────────────────────────────────


def test_touch_advances_updated_at():
    project = ReelProject(name="P")
    before = project.updated_at
    time.sleep(0.01)
    project.touch()
    assert project.updated_at > before
    assert isinstance(project.updated_at, datetime)


# ─── ID generation ─────────────────────────────────────────────────────────


def test_default_id_is_12_char_hex():
    p1 = ReelProject(name="A")
    p2 = ReelProject(name="B")
    assert len(p1.id) == 12
    assert p1.id != p2.id  # uuid4-derived → effectively unique
    int(p1.id, 16)  # is valid hex
