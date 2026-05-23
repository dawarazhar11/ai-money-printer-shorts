"""Tests for app/core/storage/project_store.py.

Covers atomic writes, the .index.json round-trip, duplicate semantics,
list filtering, and rebuild_index.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.models import ReelProject
from core.models.project import Segment


def _make_project(name: str = "Test Project", status: str = "draft") -> ReelProject:
    return ReelProject(
        name=name,
        status=status,
        raw_script="Hello world.",
        segments=[
            Segment(index=0, kind="a_roll", text="Intro narration"),
            Segment(index=1, kind="b_roll", text="cutaway scene"),
        ],
    )


# ─── Basic CRUD ─────────────────────────────────────────────────────────────


def test_save_creates_project_file_and_indexes(isolated_store):
    project = _make_project()
    isolated_store.save(project)

    assert isolated_store.project_file(project.id).exists()
    index = json.loads(isolated_store.index_path.read_text())
    assert project.id in index["projects"]
    assert index["projects"][project.id]["name"] == "Test Project"


def test_load_returns_persisted_project(isolated_store):
    project = _make_project(name="LoadMe")
    isolated_store.save(project)

    loaded = isolated_store.load(project.id)
    assert loaded is not None
    assert loaded.id == project.id
    assert loaded.name == "LoadMe"
    assert len(loaded.segments) == 2
    assert loaded.segments[0].kind == "a_roll"


def test_load_missing_returns_none(isolated_store):
    assert isolated_store.load("does-not-exist") is None


def test_delete_removes_project_and_index_entry(isolated_store):
    project = _make_project()
    isolated_store.save(project)

    assert isolated_store.delete(project.id)
    assert not isolated_store.project_dir(project.id).exists()

    index = json.loads(isolated_store.index_path.read_text())
    assert project.id not in index["projects"]


# ─── Atomic write — no stray .tmp files ────────────────────────────────────


def test_save_leaves_no_tmp_files(isolated_store):
    project = _make_project()
    isolated_store.save(project)

    leftovers = list(isolated_store.project_dir(project.id).glob("*.tmp"))
    assert leftovers == []


# ─── duplicate() ───────────────────────────────────────────────────────────


def test_duplicate_creates_fresh_project(isolated_store):
    original = _make_project(name="Original")
    original.status = "completed"
    isolated_store.save(original)

    clone = isolated_store.duplicate(original.id, new_name="Clone")
    assert clone is not None
    assert clone.id != original.id
    assert clone.name == "Clone"
    assert clone.status == "draft"
    # segments reset to pending
    assert all(s.status == "pending" for s in clone.segments)
    # both projects present on disk
    assert isolated_store.load(original.id) is not None
    assert isolated_store.load(clone.id) is not None


def test_duplicate_missing_returns_none(isolated_store):
    assert isolated_store.duplicate("nope") is None


def test_duplicate_default_name_suffix(isolated_store):
    original = _make_project(name="Source")
    isolated_store.save(original)
    clone = isolated_store.duplicate(original.id)
    assert clone is not None
    assert clone.name == "Source (copy)"


# ─── list() filtering and sorting ──────────────────────────────────────────


def test_list_filters_by_status(isolated_store):
    isolated_store.save(_make_project(name="A", status="draft"))
    isolated_store.save(_make_project(name="B", status="completed"))
    isolated_store.save(_make_project(name="C", status="completed"))

    completed = isolated_store.list(status="completed")
    assert len(completed) == 2
    assert {r["name"] for r in completed} == {"B", "C"}


def test_list_respects_limit_and_offset(isolated_store):
    for i in range(5):
        isolated_store.save(_make_project(name=f"P{i}"))

    page1 = isolated_store.list(limit=2, offset=0)
    page2 = isolated_store.list(limit=2, offset=2)
    assert len(page1) == 2
    assert len(page2) == 2
    assert {r["id"] for r in page1}.isdisjoint({r["id"] for r in page2})


# ─── stats ─────────────────────────────────────────────────────────────────


def test_stats_counts_by_status(isolated_store):
    isolated_store.save(_make_project(status="draft"))
    isolated_store.save(_make_project(status="completed"))
    isolated_store.save(_make_project(status="completed"))
    isolated_store.save(_make_project(status="failed"))

    stats = isolated_store.stats()
    assert stats["total"] == 4
    assert stats["completed"] == 2
    assert stats["failed"] == 1


# ─── rebuild_index ─────────────────────────────────────────────────────────


def test_rebuild_index_recovers_from_corrupt_index(isolated_store):
    p1 = _make_project(name="P1")
    p2 = _make_project(name="P2")
    isolated_store.save(p1)
    isolated_store.save(p2)

    # Nuke the index
    isolated_store.index_path.write_text("not valid json")

    count = isolated_store.rebuild_index()
    assert count == 2
    index = json.loads(isolated_store.index_path.read_text())
    assert {p1.id, p2.id} == set(index["projects"].keys())
