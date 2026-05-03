"""Persist generated media into the project media tree.

Every async generator (Replicate, ComfyUI, HeyGen) eventually produces either a
remote URL or a temp file. We want a single place that copies the bytes into a
predictable per-project layout so downstream pipeline steps can find them.
"""

from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import requests

DEFAULT_MEDIA_ROOT = Path("media")
EXTENSION_BY_KIND = {"image": ".png", "video": ".mp4", "audio": ".mp3"}


def _media_root() -> Path:
    root = DEFAULT_MEDIA_ROOT
    root.mkdir(parents=True, exist_ok=True)
    return root


def _extension_from(source: str, fallback: str) -> str:
    suffix = Path(urlparse(source).path).suffix
    return suffix if suffix else fallback


def download_video(
    source: str,
    metadata: Mapping[str, Any] | None = None,
    backend: str = "generic",
) -> str:
    """Persist a video referenced by URL or local path into the media tree.

    `metadata` may include `type` (a-roll/b-roll), `id`, `width`, `height`.
    Returns the absolute local path of the persisted file.
    """
    metadata = dict(metadata or {})
    kind = metadata.get("kind", "video")
    media_type = metadata.get("type", "broll")
    media_id = str(metadata.get("id", f"{int(time.time())}"))

    fallback_ext = EXTENSION_BY_KIND.get(kind, ".mp4")
    extension = _extension_from(source, fallback_ext)
    target_dir = _media_root() / backend / media_type
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{media_id}{extension}"

    if source.startswith(("http://", "https://")):
        response = requests.get(source, stream=True, timeout=60)
        response.raise_for_status()
        with target.open("wb") as fh:
            for chunk in response.iter_content(chunk_size=1 << 16):
                if chunk:
                    fh.write(chunk)
    else:
        src = Path(source)
        if not src.exists():
            raise FileNotFoundError(f"Source media not found: {source}")
        if src.resolve() == target.resolve():
            return str(target.resolve())
        shutil.copy2(src, target)

    return str(target.resolve())
