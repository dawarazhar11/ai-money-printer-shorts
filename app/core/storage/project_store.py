"""JSON-backed project store with .index.json catalogue."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from ..config import config_manager
from ..logging import get_logger
from ..models import ReelProject

logger = get_logger("core.storage")


class ProjectStore:
    """CRUD for ReelProject objects, persisted as JSON files."""

    def __init__(self, base_dir: Optional[Path] = None) -> None:
        self._base_dir = base_dir  # resolved lazily so config is not read at import

    @property
    def base_dir(self) -> Path:
        if self._base_dir is None:
            self._base_dir = config_manager.config.user_data_dir
        return self._base_dir

    @property
    def index_path(self) -> Path:
        return self.base_dir / ".index.json"

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load_index(self) -> dict:
        if self.index_path.exists():
            try:
                return json.loads(self.index_path.read_text())
            except (json.JSONDecodeError, IOError) as exc:
                logger.warning(f"Corrupt index, resetting: {exc}")
        return {}

    def _save_index(self, index: dict) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.write_text(json.dumps(index, indent=2, default=str))

    def _project_path(self, project_id: str) -> Path:
        return self.base_dir / project_id / "project.json"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def save(self, project: ReelProject) -> ReelProject:
        project.touch()
        project_dir = self.base_dir / project.id
        project_dir.mkdir(parents=True, exist_ok=True)

        path = self._project_path(project.id)
        path.write_text(project.model_dump_json(indent=2))
        logger.info(f"Saved project {project.id} ({project.name})")

        # Update index
        index = self._load_index()
        index[project.id] = {
            "name": project.name,
            "updated_at": project.updated_at.isoformat(),
            "path": str(path),
        }
        self._save_index(index)
        return project

    def load(self, project_id: str) -> Optional[ReelProject]:
        path = self._project_path(project_id)
        if not path.exists():
            logger.warning(f"Project not found: {project_id}")
            return None
        try:
            data = json.loads(path.read_text())
            return ReelProject.model_validate(data)
        except Exception as exc:
            logger.error(f"Failed to load project {project_id}: {exc}")
            return None

    def delete(self, project_id: str) -> bool:
        path = self._project_path(project_id)
        if path.exists():
            path.unlink()
        index = self._load_index()
        if project_id in index:
            del index[project_id]
            self._save_index(index)
            logger.info(f"Deleted project {project_id}")
            return True
        return False

    def list_all(self) -> list[dict]:
        """Return index entries sorted newest-first."""
        index = self._load_index()
        items = list(index.values())
        items.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return items

    def get_or_create(self, name: str) -> ReelProject:
        """Find an existing project by name or create a new one."""
        for pid, meta in self._load_index().items():
            if meta.get("name") == name:
                project = self.load(pid)
                if project:
                    return project
        project = ReelProject(name=name)
        return self.save(project)


project_store = ProjectStore()
