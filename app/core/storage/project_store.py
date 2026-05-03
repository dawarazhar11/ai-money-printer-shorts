"""Filesystem-backed ReelProject store with index for fast listing.

On-disk layout (under storage.user_data_dir, default `app/config/user_data/`):

    projects/
    ├── .index.json                        # cached project summaries
    ├── {project_id}/
    │   ├── project.json                   # full ReelProject (Pydantic)
    │   ├── settings.json                  # legacy ReelForge per-project settings
    │   ├── segments.json                  # legacy
    │   └── media/                         # generated assets

Writes are atomic (tmp file + rename) so a crash mid-write can't corrupt the
index. Adapted from Pixelle-Video persistence.py + history_manager.py
(Apache 2.0).
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Literal, Optional
from uuid import uuid4

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import ReelProject

logger = get_logger("storage.projects")

INDEX_VERSION = "1"
SortField = Literal["created_at", "updated_at", "name", "duration"]
SortOrder = Literal["asc", "desc"]


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


class ProjectStore:
    """Singleton project store. Thread-safe writes via a per-instance lock."""

    _instance: Optional["ProjectStore"] = None
    _singleton_lock = Lock()

    def __new__(cls, root: Optional[Path] = None):
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
            return cls._instance

    def __init__(self, root: Optional[Path] = None):
        if getattr(self, "_initialized", False):
            return
        base = Path(root) if root else Path(config_manager.storage().user_data_dir)
        self.root = base / "projects"
        self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / ".index.json"
        self._write_lock = Lock()
        self._ensure_index()
        self._initialized = True
        logger.info(f"ProjectStore rooted at {self.root}")

    # ── paths ──────────────────────────────────────────────────────────────

    def project_dir(self, project_id: str) -> Path:
        return self.root / project_id

    def project_file(self, project_id: str) -> Path:
        return self.project_dir(project_id) / "project.json"

    def media_dir(self, project_id: str) -> Path:
        d = self.project_dir(project_id) / "media"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── core CRUD ──────────────────────────────────────────────────────────

    def save(self, project: ReelProject) -> None:
        with self._write_lock:
            project.touch()
            path = self.project_file(project.id)
            payload = project.model_dump_json(indent=2)
            _atomic_write_text(path, payload)
            self._reindex(project)
            logger.debug(f"Saved project {project.id} ({project.name})")

    def load(self, project_id: str) -> Optional[ReelProject]:
        path = self.project_file(project_id)
        if not path.exists():
            return None
        try:
            return ReelProject.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error(f"Failed to load project {project_id}: {exc}")
            return None

    def delete(self, project_id: str) -> bool:
        with self._write_lock:
            d = self.project_dir(project_id)
            if d.exists():
                shutil.rmtree(d)
                logger.info(f"Deleted project {project_id}")
            self._drop_from_index(project_id)
            return True

    def duplicate(self, project_id: str, new_name: Optional[str] = None) -> Optional[ReelProject]:
        original = self.load(project_id)
        if original is None:
            return None
        clone = original.model_copy(deep=True)
        clone.id = uuid4().hex[:12]  # fresh id
        clone.name = new_name or f"{original.name} (copy)"
        clone.status = "draft"
        clone.created_at = datetime.now()
        clone.updated_at = datetime.now()
        clone.completed_at = None
        clone.final_video = None
        clone.captioned_video = None
        clone.published_to = {}
        for seg in clone.segments:
            seg.status = "pending"
            seg.audio = None
            seg.visual = None
            seg.composed = None
            seg.error = None
        self.save(clone)
        return clone

    # ── listing / index ────────────────────────────────────────────────────

    def list(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: SortField = "updated_at",
        sort_order: SortOrder = "desc",
    ) -> list[dict]:
        index = self._load_index()
        rows = list(index.get("projects", {}).values())

        if status:
            rows = [r for r in rows if r.get("status") == status]

        def keyfn(row: dict):
            value = row.get(sort_by, "")
            return value if value is not None else ""

        rows.sort(key=keyfn, reverse=(sort_order == "desc"))
        return rows[offset : offset + limit]

    def stats(self) -> dict:
        rows = list(self._load_index().get("projects", {}).values())
        return {
            "total": len(rows),
            "completed": sum(1 for r in rows if r.get("status") == "completed"),
            "failed": sum(1 for r in rows if r.get("status") == "failed"),
            "in_progress": sum(1 for r in rows if r.get("status") == "in_progress"),
            "total_duration": sum(r.get("duration") or 0 for r in rows),
        }

    def rebuild_index(self) -> int:
        """Re-scan project_dirs and rewrite .index.json. Returns count."""
        with self._write_lock:
            entries: dict[str, dict] = {}
            for child in self.root.iterdir():
                if not child.is_dir() or child.name.startswith("."):
                    continue
                project = self.load(child.name)
                if project:
                    entries[project.id] = self._summarize(project)
            self._write_index({"version": INDEX_VERSION, "projects": entries})
            logger.info(f"Index rebuilt: {len(entries)} projects")
            return len(entries)

    # ── internals ──────────────────────────────────────────────────────────

    def _ensure_index(self) -> None:
        if not self.index_path.exists():
            self._write_index({"version": INDEX_VERSION, "projects": {}})

    def _load_index(self) -> dict:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning(f"Index unreadable, returning empty: {exc}")
            return {"version": INDEX_VERSION, "projects": {}}

    def _write_index(self, data: dict) -> None:
        data["last_updated"] = datetime.now().isoformat()
        _atomic_write_text(self.index_path, json.dumps(data, indent=2, ensure_ascii=False))

    def _reindex(self, project: ReelProject) -> None:
        index = self._load_index()
        index.setdefault("projects", {})[project.id] = self._summarize(project)
        self._write_index(index)

    def _drop_from_index(self, project_id: str) -> None:
        index = self._load_index()
        index.get("projects", {}).pop(project_id, None)
        self._write_index(index)

    @staticmethod
    def _summarize(project: ReelProject) -> dict:
        final = project.final_video
        return {
            "id": project.id,
            "name": project.name,
            "status": project.status,
            "created_at": project.created_at.isoformat(),
            "updated_at": project.updated_at.isoformat(),
            "completed_at": project.completed_at.isoformat() if project.completed_at else None,
            "n_segments": len(project.segments),
            "n_a_roll": len(project.a_roll),
            "n_b_roll": len(project.b_roll),
            "duration": project.total_duration,
            "progress": project.progress,
            "final_video_path": str(final.path) if final else None,
            "size_bytes": final.size_bytes if final else 0,
            "published_to": list(project.published_to.keys()),
        }


# module-level singleton
project_store = ProjectStore()
