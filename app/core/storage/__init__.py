"""Project persistence: filesystem-backed JSON store with index.

Adapted from Pixelle-Video's pixelle_video/services/persistence.py and
history_manager.py (Apache 2.0). Two key changes for ReelForge:

  1. Synchronous API (no async/await). ReelForge runs inside Streamlit reruns;
     async would force every page to manage an event loop.
  2. Pydantic v2 native serialization (model_dump_json / model_validate_json),
     so we don't hand-write to/from-dict per model. Adding a field is a
     one-line change instead of touching three serializers.
"""

from .project_store import ProjectStore, project_store

__all__ = ["ProjectStore", "project_store"]
