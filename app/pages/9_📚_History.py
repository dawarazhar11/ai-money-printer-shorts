"""History page — list, resume, duplicate, and delete past ReelForge projects.

Adapted from Pixelle-Video's web/pages/2_📚_History.py (Apache 2.0). Reads
from app.core.storage.project_store, the ProjectStore singleton built on
top of the new ReelProject domain model.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from core.logging import get_logger  # noqa: E402
from core.storage import project_store  # noqa: E402

logger = get_logger("pages.history")

st.set_page_config(
    page_title="History | RealForge",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📚 Project History")
st.caption("Resume drafts, re-publish completed projects, or duplicate a working setup.")


# ── Filters ────────────────────────────────────────────────────────────────
top = st.columns([2, 2, 2, 1])
with top[0]:
    status_filter = st.selectbox(
        "Status",
        options=["all", "draft", "in_progress", "completed", "failed", "archived"],
        index=0,
    )
with top[1]:
    sort_by = st.selectbox("Sort by", options=["updated_at", "created_at", "name", "duration"], index=0)
with top[2]:
    sort_order = st.selectbox("Order", options=["desc", "asc"], index=0)
with top[3]:
    if st.button("🔄 Rebuild index", help="Rescan project_dir; useful after manual file changes"):
        n = project_store.rebuild_index()
        st.success(f"Rebuilt index: {n} project(s)")


# ── Stats card ─────────────────────────────────────────────────────────────
stats = project_store.stats()
m = st.columns(4)
m[0].metric("Total", stats["total"])
m[1].metric("Completed", stats["completed"])
m[2].metric("In progress", stats["in_progress"])
m[3].metric("Total minutes", round(stats["total_duration"] / 60, 1))

st.divider()

# ── Listing ────────────────────────────────────────────────────────────────
status = None if status_filter == "all" else status_filter
rows = project_store.list(status=status, sort_by=sort_by, sort_order=sort_order, limit=100)

if not rows:
    st.info("No projects yet. Head to Settings to start a new one.")
    st.stop()


def _fmt_dt(value):
    if not value:
        return "—"
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return value


def _fmt_duration(seconds):
    if not seconds:
        return "—"
    m_, s_ = divmod(int(seconds), 60)
    return f"{m_}m {s_:02d}s"


for row in rows:
    project_id = row["id"]
    with st.container(border=True):
        cols = st.columns([3, 2, 2, 2, 3])

        with cols[0]:
            st.markdown(f"### {row['name']}")
            st.caption(f"ID `{project_id}`")
            st.write(f"**Status:** {row['status']}")

        with cols[1]:
            st.metric("Segments", row["n_segments"])
            st.caption(f"A-Roll: {row['n_a_roll']} • B-Roll: {row['n_b_roll']}")

        with cols[2]:
            st.metric("Duration", _fmt_duration(row["duration"]))
            st.caption(f"Updated: {_fmt_dt(row['updated_at'])}")

        with cols[3]:
            progress = row.get("progress", 0.0)
            st.metric("Progress", f"{int(progress * 100)}%")
            published = ", ".join(row.get("published_to", [])) or "—"
            st.caption(f"Published: {published}")

        with cols[4]:
            video_path = row.get("final_video_path")
            if video_path and Path(video_path).exists():
                with open(video_path, "rb") as fh:
                    st.download_button(
                        "⬇️ Download MP4",
                        data=fh,
                        file_name=Path(video_path).name,
                        mime="video/mp4",
                        key=f"dl_{project_id}",
                    )
            actions = st.columns(3)
            with actions[0]:
                if st.button("📂 Open", key=f"open_{project_id}"):
                    st.session_state["active_project_id"] = project_id
                    st.success(f"Loaded {row['name']} — go to Settings to continue")
            with actions[1]:
                if st.button("📋 Duplicate", key=f"dup_{project_id}"):
                    clone = project_store.duplicate(project_id)
                    if clone:
                        st.success(f"Duplicated as {clone.name}")
                        st.rerun()
                    else:
                        st.error("Duplicate failed")
            with actions[2]:
                if st.button("🗑️ Delete", key=f"del_{project_id}"):
                    if st.session_state.get(f"confirm_del_{project_id}"):
                        project_store.delete(project_id)
                        st.session_state.pop(f"confirm_del_{project_id}", None)
                        st.success("Deleted")
                        st.rerun()
                    else:
                        st.session_state[f"confirm_del_{project_id}"] = True
                        st.warning("Click Delete again to confirm")
