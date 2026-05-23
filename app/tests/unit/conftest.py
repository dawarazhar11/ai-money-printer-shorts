"""Pytest fixtures for ReelForge unit tests.

Puts `app/` on sys.path so tests can `from core.X import ...` exactly like
the Streamlit pages do at runtime. Also exposes an isolated config_manager
fixture that points at a tmp_path config.yaml — no cross-test pollution.
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Iterator

import pytest

# Make app/ importable as the source root.
APP_DIR = Path(__file__).resolve().parents[2]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))


def _reset_config_singleton() -> None:
    """ConfigManager is a process-level singleton — wipe it between tests."""
    from core.config import manager as manager_mod

    manager_mod.ConfigManager._instance = None


@pytest.fixture
def isolated_config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator:
    """Yield a fresh ConfigManager backed by tmp_path/config.yaml.

    Re-imports the manager so the singleton is built against the tmp path.
    """
    cfg_path = tmp_path / "config.yaml"
    monkeypatch.setenv("REELFORGE_CONFIG", str(cfg_path))

    _reset_config_singleton()
    from core.config import manager as manager_mod

    importlib.reload(manager_mod)
    yield manager_mod.config_manager

    _reset_config_singleton()


@pytest.fixture
def isolated_user_data(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, isolated_config) -> Path:
    """Point storage.user_data_dir at tmp_path and return its Path."""
    user_data = tmp_path / "user_data"
    user_data.mkdir(parents=True, exist_ok=True)
    isolated_config.update({"storage": {"user_data_dir": str(user_data)}})
    isolated_config.save()
    return user_data


def _project_store_module():
    # __init__.py shadows the submodule name with the singleton instance, so
    # we have to go via importlib to reach the actual module object.
    return importlib.import_module("core.storage.project_store")


def _reset_project_store_singleton() -> None:
    _project_store_module().ProjectStore._instance = None


@pytest.fixture
def isolated_store(isolated_user_data: Path):
    """Yield a fresh ProjectStore rooted at the isolated user_data dir.

    `core.config.__init__` binds `config_manager` at first import, so the
    project_store module's view is stale across test runs. We sidestep that
    by constructing ProjectStore with an explicit `root` after resetting
    the singleton — the constructor uses `root` directly when provided.
    """
    ps_mod = _project_store_module()
    _reset_project_store_singleton()
    store = ps_mod.ProjectStore(root=isolated_user_data)
    yield store
    _reset_project_store_singleton()
