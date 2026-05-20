"""Workflow discovery and resolution.

Adapted from Pixelle-Video's pixelle_video/services/comfy_base_service.py
(Apache 2.0). Two-tier layout for execution backend:

  app/workflows/
    selfhost/   ← runs on local ComfyUI server
    cloud/      ← runs on RunningHub (Pixelle's cloud ComfyUI host)

Resolution rules:
  - `resolve("wan.json")`           → first match in selfhost/, then cloud/
  - `resolve("image_flux.json")`    → same
  - `resolve("cloud/image_flux.json")` → forced cloud path
  - `resolve("/abs/path.json")`     → returned as-is if exists
  - `discover("image")`             → all `image_*.json` from both dirs

Backwards-compat: if a name isn't found in selfhost/ or cloud/, we fall back
to the legacy flat `app/workflows/` layout used by older code. That makes
this safe to introduce without touching every caller.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal, Optional

from config import WORKFLOWS_DIR
from core.logging import get_logger

logger = get_logger("services.workflows")

Backend = Literal["selfhost", "cloud"]
WORKFLOW_PREFIXES = ("image_", "video_", "tts_", "digital_", "i2v_")


def selfhost_dir() -> Path:
    return WORKFLOWS_DIR / "selfhost"


def cloud_dir() -> Path:
    return WORKFLOWS_DIR / "cloud"


def resolve(name: str) -> Path:
    """Find a workflow file by name. Raises FileNotFoundError if not found."""
    p = Path(name)

    # Absolute / qualified path
    if p.is_absolute():
        if p.exists():
            return p
        raise FileNotFoundError(f"Workflow not found: {p}")

    # Backend-prefixed (e.g., "cloud/image_flux.json")
    if len(p.parts) > 1 and p.parts[0] in ("selfhost", "cloud"):
        full = WORKFLOWS_DIR / p
        if full.exists():
            return full
        raise FileNotFoundError(f"Workflow not found: {full}")

    # Bare name → search selfhost → cloud → legacy flat
    for candidate in (selfhost_dir() / p.name, cloud_dir() / p.name, WORKFLOWS_DIR / p.name):
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"Workflow not found in selfhost/, cloud/, or legacy: {p.name}")


def discover(prefix: str, backend: Optional[Backend] = None) -> dict[str, Path]:
    """List workflows whose filename starts with `{prefix}_` (sans the trailing _).

    Returns {filename → path}. If `backend` is None, both dirs are merged
    (selfhost wins on collision because it's checked first).
    """
    needle = prefix if prefix.endswith("_") else f"{prefix}_"
    out: dict[str, Path] = {}
    sources: list[Path] = []
    if backend in (None, "cloud"):
        sources.append(cloud_dir())
    if backend in (None, "selfhost"):
        sources.append(selfhost_dir())
    for src in sources:
        if not src.exists():
            continue
        for entry in sorted(src.glob(f"{needle}*.json")):
            out[entry.name] = entry  # later entries override (selfhost last → wins)
    return out


def list_all(backend: Optional[Backend] = None) -> dict[Backend, dict[str, Path]]:
    """Return all workflows grouped by backend, then by prefix."""
    result: dict[Backend, dict[str, Path]] = {}
    backends: list[Backend] = ["selfhost", "cloud"] if backend is None else [backend]
    for b in backends:
        result[b] = {p.name: p for p in (selfhost_dir() if b == "selfhost" else cloud_dir()).glob("*.json")}
    return result
