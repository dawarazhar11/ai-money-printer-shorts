"""Tests for app/services/workflows.py — discovery and resolution."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest


@pytest.fixture
def workflow_tree(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Lay out a tmp WORKFLOWS_DIR with selfhost/, cloud/, and legacy flat files.

    Reloads `services.workflows` so it picks up the patched WORKFLOWS_DIR.
    """
    selfhost = tmp_path / "selfhost"
    cloud = tmp_path / "cloud"
    selfhost.mkdir()
    cloud.mkdir()

    # selfhost workflows
    (selfhost / "image_flux.json").write_text("{}")
    (selfhost / "image_qwen.json").write_text("{}")
    (selfhost / "video_wan.json").write_text("{}")
    (selfhost / "tts_edge.json").write_text("{}")

    # cloud workflows (one collides with selfhost on purpose)
    (cloud / "image_flux.json").write_text("{}")     # collision
    (cloud / "image_sdxl.json").write_text("{}")
    (cloud / "i2v_LTX2.json").write_text("{}")

    # legacy flat file (fallback path)
    (tmp_path / "legacy.json").write_text("{}")

    # Patch BOTH the `config` module's constant and the already-imported
    # binding inside `services.workflows`.
    import config as config_mod

    monkeypatch.setattr(config_mod, "WORKFLOWS_DIR", tmp_path)

    import services.workflows as wf_mod

    importlib.reload(wf_mod)
    return wf_mod, tmp_path


# ─── resolve() ─────────────────────────────────────────────────────────────


def test_resolve_bare_name_finds_in_selfhost_first(workflow_tree):
    wf, root = workflow_tree
    result = wf.resolve("image_flux.json")
    assert result == root / "selfhost" / "image_flux.json"


def test_resolve_bare_name_finds_in_cloud_when_only_there(workflow_tree):
    wf, root = workflow_tree
    result = wf.resolve("image_sdxl.json")
    assert result == root / "cloud" / "image_sdxl.json"


def test_resolve_bare_name_falls_back_to_legacy_flat(workflow_tree):
    wf, root = workflow_tree
    result = wf.resolve("legacy.json")
    assert result == root / "legacy.json"


def test_resolve_qualified_path_forces_backend(workflow_tree):
    wf, root = workflow_tree
    result = wf.resolve("cloud/image_flux.json")
    assert result == root / "cloud" / "image_flux.json"


def test_resolve_absolute_path_returned_as_is(workflow_tree, tmp_path):
    wf, _ = workflow_tree
    abs_file = tmp_path / "absolute.json"
    abs_file.write_text("{}")
    assert wf.resolve(str(abs_file)) == abs_file


def test_resolve_missing_raises_file_not_found(workflow_tree):
    wf, _ = workflow_tree
    with pytest.raises(FileNotFoundError):
        wf.resolve("nonexistent_workflow.json")


def test_resolve_qualified_missing_raises_file_not_found(workflow_tree):
    wf, _ = workflow_tree
    with pytest.raises(FileNotFoundError):
        wf.resolve("cloud/missing.json")


# ─── discover() ────────────────────────────────────────────────────────────


def test_discover_filters_by_prefix(workflow_tree):
    wf, _ = workflow_tree
    images = wf.discover("image")
    assert set(images.keys()) == {"image_flux.json", "image_qwen.json", "image_sdxl.json"}


def test_discover_with_backend_filter(workflow_tree):
    wf, root = workflow_tree
    selfhost_only = wf.discover("image", backend="selfhost")
    assert set(selfhost_only.keys()) == {"image_flux.json", "image_qwen.json"}
    # Paths point to selfhost dir
    assert all(p.parent.name == "selfhost" for p in selfhost_only.values())


def test_discover_selfhost_wins_on_name_collision(workflow_tree):
    wf, root = workflow_tree
    images = wf.discover("image")
    # image_flux.json exists in both; selfhost should win because it's
    # iterated last (later entries override).
    assert images["image_flux.json"] == root / "selfhost" / "image_flux.json"


def test_discover_accepts_prefix_with_or_without_underscore(workflow_tree):
    wf, _ = workflow_tree
    with_under = wf.discover("image_")
    without_under = wf.discover("image")
    assert set(with_under.keys()) == set(without_under.keys())


def test_discover_empty_when_prefix_unknown(workflow_tree):
    wf, _ = workflow_tree
    assert wf.discover("unknownprefix") == {}


# ─── list_all() ────────────────────────────────────────────────────────────


def test_list_all_groups_by_backend(workflow_tree):
    wf, _ = workflow_tree
    grouped = wf.list_all()
    assert set(grouped.keys()) == {"selfhost", "cloud"}
    assert set(grouped["selfhost"].keys()) == {
        "image_flux.json", "image_qwen.json", "video_wan.json", "tts_edge.json"
    }
    assert set(grouped["cloud"].keys()) == {
        "image_flux.json", "image_sdxl.json", "i2v_LTX2.json"
    }


def test_list_all_with_backend_filter_returns_only_one(workflow_tree):
    wf, _ = workflow_tree
    only_cloud = wf.list_all(backend="cloud")
    assert set(only_cloud.keys()) == {"cloud"}
