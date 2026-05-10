import json
from pathlib import Path
from typing import List, Optional

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import ReelProject, Segment, MediaAsset

logger = get_logger("core.storage.project_store")

_INDEX_FILE = "index.json"


def _index_path() -> Path:
    return config_manager.config.user_data_dir / _INDEX_FILE


def _project_dir(project_id: str) -> Path:
    return config_manager.config.user_data_dir / project_id


def _load_index() -> dict:
    idx = _index_path()
    if idx.exists():
        try:
            return json.loads(idx.read_text())
        except json.JSONDecodeError:
            logger.warning("Corrupt index.json — starting fresh")
    return {}


def _save_index(data: dict) -> None:
    idx = _index_path()
    idx.parent.mkdir(parents=True, exist_ok=True)
    idx.write_text(json.dumps(data, indent=2))


def _segment_from_dict(d: dict) -> Segment:
    asset_d = d.get("media_asset")
    asset = None
    if asset_d:
        asset = MediaAsset(
            path=asset_d.get("path", ""),
            asset_type=asset_d.get("asset_type", "video"),
            duration=asset_d.get("duration"),
            metadata=asset_d.get("metadata", {}),
        )
    return Segment(
        id=d["id"],
        type=d.get("type", ""),
        content=d.get("content", ""),
        media_asset=asset,
        status=d.get("status", "not_started"),
        metadata=d.get("metadata", {}),
    )


def _segment_to_dict(s: Segment) -> dict:
    asset_d = None
    if s.media_asset:
        asset_d = {
            "path": s.media_asset.path,
            "asset_type": s.media_asset.asset_type,
            "duration": s.media_asset.duration,
            "metadata": s.media_asset.metadata,
        }
    return {
        "id": s.id,
        "type": s.type,
        "content": s.content,
        "media_asset": asset_d,
        "status": s.status,
        "metadata": s.metadata,
    }


def _project_from_dict(d: dict) -> ReelProject:
    return ReelProject(
        id=d["id"],
        name=d.get("name", d["id"]),
        path=d.get("path", ""),
        segments=[_segment_from_dict(s) for s in d.get("segments", [])],
        metadata=d.get("metadata", {}),
    )


def _project_to_dict(p: ReelProject) -> dict:
    return {
        "id": p.id,
        "name": p.name,
        "path": p.path,
        "segments": [_segment_to_dict(s) for s in p.segments],
        "metadata": p.metadata,
    }


class _ProjectStore:
    def load(self, project_id: str) -> Optional[ReelProject]:
        pdir = _project_dir(project_id)
        pfile = pdir / "project.json"
        if not pfile.exists():
            logger.warning("Project not found: %s", project_id)
            return None
        try:
            data = json.loads(pfile.read_text())
            return _project_from_dict(data)
        except Exception as exc:
            logger.error("Failed to load project %s: %s", project_id, exc)
            return None

    def save(self, project: ReelProject) -> None:
        pdir = _project_dir(project.id)
        pdir.mkdir(parents=True, exist_ok=True)
        pfile = pdir / "project.json"
        pfile.write_text(json.dumps(_project_to_dict(project), indent=2))
        idx = _load_index()
        idx[project.id] = {"id": project.id, "name": project.name, "path": str(pdir)}
        _save_index(idx)
        logger.info("Saved project %s", project.id)

    def list_all(self) -> List[ReelProject]:
        idx = _load_index()
        projects = []
        for pid in idx:
            p = self.load(pid)
            if p:
                projects.append(p)
        return projects

    def delete(self, project_id: str) -> bool:
        import shutil
        pdir = _project_dir(project_id)
        if pdir.exists():
            shutil.rmtree(pdir)
        idx = _load_index()
        idx.pop(project_id, None)
        _save_index(idx)
        logger.info("Deleted project %s", project_id)
        return True


project_store = _ProjectStore()
