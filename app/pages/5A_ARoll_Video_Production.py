import streamlit as st
import os
import sys
import json
import time
from pathlib import Path

# Add app root to path
_app_root = Path(__file__).parent.parent.absolute()
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

try:
    from components.custom_navigation import render_custom_sidebar, render_horizontal_navigation, render_step_navigation
    from components.progress import render_step_header
    from utils.session_state import get_settings, get_project_path, mark_step_complete
except ImportError as e:
    st.error(f"Failed to import local modules: {e}")
    st.stop()

from app.core.config import config_manager
from app.core.logging import get_logger
from app.services.heygen_service import heygen_service
from app.services.tts_service import edge_tts_service

logger = get_logger("pages.5a")

st.set_page_config(
    page_title="A-Roll Video Production | ReelForge",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded",
)

def load_css():
    css_file = Path("assets/css/style.css")
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

load_css()

st.markdown("""
<style>
    .horizontal-nav { margin-bottom:20px; padding:10px; background-color:#f0f2f6; border-radius:10px; }
    [data-testid="stSidebar"] { background-color:white !important; }
    [data-testid="stSidebar"] * { color:black !important; }
    [data-testid="stSidebar"] button { background-color:#e6f2ff !important; color:#0066cc !important; border-radius:6px !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='horizontal-nav'>", unsafe_allow_html=True)
render_horizontal_navigation()
st.markdown("</div>", unsafe_allow_html=True)
render_custom_sidebar()

settings = get_settings()
project_path = get_project_path()

# ── session state ──────────────────────────────────────────────────────────
_defaults = {
    "segments": [],
    "aroll_status": {},
    "aroll_fetch_ids": {},
    "avatar_type": "video",
    "heygen_avatar_id": "Abigail_expressive_2024112501",
    "heygen_voice_id": "fe612bdf07a94d5fa7b80bf1282937d1",
    "heygen_photo_avatar_id": "35e0f2af72874fd6bc6e20cb74aebe72",
    "manual_upload": False,
    "uploaded_files": {},
    "manual_ids": {},
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── helpers ────────────────────────────────────────────────────────────────
def _status_path() -> Path:
    return project_path / "aroll_status.json"

def _fetch_ids_path() -> Path:
    return project_path / "aroll_fetch_ids.json"

def load_script_data() -> bool:
    script_file = project_path / "script.json"
    if not script_file.exists():
        logger.warning(f"Script file not found: {script_file}")
        return False
    try:
        data = json.loads(script_file.read_text())
        segs = [s for s in data.get("segments", []) if isinstance(s, dict) and s.get("type") == "A-Roll"]
        if segs:
            st.session_state.segments = segs
            logger.info(f"Loaded {len(segs)} A-Roll segments")
            return True
        logger.warning("No valid A-Roll segments found")
        return False
    except json.JSONDecodeError:
        logger.error("Failed to parse script.json")
        return False

def load_aroll_status() -> bool:
    p = _status_path()
    if p.exists():
        try:
            st.session_state.aroll_status = json.loads(p.read_text())
            return True
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading A-Roll status: {e}")
    return False

def save_aroll_status() -> None:
    try:
        _status_path().write_text(json.dumps(st.session_state.aroll_status, indent=2))
    except IOError as e:
        logger.error(f"Error saving A-Roll status: {e}")

def save_fetch_ids() -> None:
    try:
        _fetch_ids_path().write_text(json.dumps(st.session_state.aroll_fetch_ids, indent=2))
    except IOError as e:
        logger.error(f"Error saving fetch IDs: {e}")

def save_media_content(content: bytes, segment_id: str) -> dict:
    media_dir = project_path / "media" / "a-roll"
    media_dir.mkdir(parents=True, exist_ok=True)
    file_path = media_dir / f"{segment_id}.mp4"
    try:
        file_path.write_bytes(content)
        logger.info(f"Saved media to {file_path}")
        return {"status": "success", "file_path": str(file_path)}
    except Exception as e:
        logger.error(f"Error saving media: {e}")
        return {"status": "error", "message": str(e)}


# ── A-Roll generation ──────────────────────────────────────────────────────
def _edge_tts_fallback(segment_id: str, text: str) -> None:
    """Use Edge-TTS when HeyGen is not configured."""
    output_dir = project_path / "media" / "a-roll"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / f"{segment_id}.mp3")
    try:
        asset = edge_tts_service.synthesize_sync(text=text, output_path=output_path)
        st.session_state.aroll_status[segment_id] = {
            "status": "completed",
            "message": "Generated via Edge-TTS (HeyGen fallback)",
            "local_path": asset.file_path,
            "timestamp": time.time(),
        }
        logger.info(f"Edge-TTS fallback done for {segment_id}: {asset.file_path}")
    except Exception as e:
        logger.error(f"Edge-TTS fallback failed for {segment_id}: {e}")
        st.session_state.aroll_status[segment_id] = {
            "status": "error",
            "message": f"Edge-TTS error: {e}",
        }

def generate_aroll_content(segments: list, avatar_type: str) -> dict:
    heygen_ok = config_manager.config.is_heygen_configured()
    if not heygen_ok:
        logger.warning("HeyGen not configured — using Edge-TTS fallback for all segments")

    results = {"status": "success", "generated": 0, "errors": {}, "videos": {}}
    avatar_id = st.session_state.heygen_avatar_id if avatar_type == "video" else st.session_state.heygen_photo_avatar_id
    voice_id = st.session_state.heygen_voice_id

    for segment in segments:
        seg_id = segment.get("id", "")
        text = segment.get("content", "").strip()
        if not seg_id or not text:
            continue

        st.session_state.aroll_status[seg_id] = {"status": "processing", "message": "Submitting…"}
        save_aroll_status()

        if not heygen_ok:
            _edge_tts_fallback(seg_id, text)
            save_aroll_status()
            results["generated"] += 1
            continue

        try:
            asset = heygen_service.synthesize_avatar(
                text=text,
                avatar_id=avatar_id,
                voice_id=voice_id,
                avatar_type=avatar_type,
                output_dir=project_path / "media" / "a-roll",
                segment_id=seg_id,
            )
            st.session_state.aroll_status[seg_id] = {
                "status": "completed",
                "message": "Generated via HeyGen",
                "local_path": asset.file_path,
                "video_id": asset.metadata.get("video_id", ""),
                "timestamp": time.time(),
            }
            st.session_state.aroll_fetch_ids[seg_id] = asset.metadata.get("video_id", "")
            results["generated"] += 1
            results["videos"][seg_id] = asset.metadata.get("video_id", "")
        except Exception as e:
            logger.error(f"HeyGen failed for {seg_id}: {e}")
            st.session_state.aroll_status[seg_id] = {"status": "error", "message": str(e)}
            results["errors"][seg_id] = str(e)

        save_aroll_status()
        save_fetch_ids()

    if results["generated"] == 0:
        results["status"] = "error"
        results["message"] = "Failed to generate any A-Roll videos"
    return results


def check_aroll_status_from_heygen() -> dict:
    results = {"status": "success", "checked": 0, "completed": 0, "errors": {}}
    for seg_id, video_id in st.session_state.aroll_fetch_ids.items():
        if not video_id:
            continue
        try:
            data = heygen_service.check_video_status(video_id)
            status = data.get("status", "").lower()
            video_url = data.get("video_url", "")
            st.session_state.aroll_status[seg_id] = {
                "status": status,
                "message": f"Status: {status}",
                "video_id": video_id,
                "video_url": video_url,
                "timestamp": time.time(),
            }
            results["checked"] += 1
            if status in {"completed", "ready", "success", "done"} and video_url:
                out_dir = project_path / "media" / "a-roll"
                out_dir.mkdir(parents=True, exist_ok=True)
                out_path = str(out_dir / f"{seg_id}.mp4")
                dl = heygen_service.download_video(video_url, out_path)
                if dl.get("status") == "success":
                    st.session_state.aroll_status[seg_id]["local_path"] = out_path
                    st.session_state.aroll_status[seg_id]["downloaded"] = True
                    results["completed"] += 1
        except Exception as e:
            logger.error(f"Status check failed for {seg_id}: {e}")
            st.session_state.aroll_status[seg_id] = {"status": "error", "message": str(e)}
            results["errors"][seg_id] = str(e)
        save_aroll_status()
    return results


def manual_fetch_content(segment_ids: dict) -> dict:
    results = {"status": "success", "checked": 0, "completed": 0, "errors": {}}
    for seg_id, video_id in segment_ids.items():
        if not video_id:
            continue
        st.session_state.aroll_status[seg_id] = {"status": "fetching", "message": f"Fetching {video_id}", "video_id": video_id, "timestamp": time.time()}
        save_aroll_status()
        try:
            data = heygen_service.check_video_status(video_id)
            status = data.get("status", "").lower()
            video_url = data.get("video_url", "")
            st.session_state.aroll_fetch_ids[seg_id] = video_id
            st.session_state.aroll_status[seg_id] = {"status": status, "message": f"Status: {status}", "video_id": video_id, "video_url": video_url, "timestamp": time.time()}
            results["checked"] += 1
            if status in {"completed", "ready", "success", "done"} and video_url:
                out_path = str(project_path / "media" / "a-roll" / f"{seg_id}.mp4")
                dl = heygen_service.download_video(video_url, out_path)
                if dl.get("status") == "success":
                    st.session_state.aroll_status[seg_id]["local_path"] = out_path
                    results["completed"] += 1
        except Exception as e:
            logger.error(f"Fetch failed for {seg_id}: {e}")
            results["errors"][seg_id] = str(e)
        save_aroll_status()
        save_fetch_ids()
    return results


def handle_manual_uploads(uploaded_files: dict) -> None:
    for seg_id, f in uploaded_files.items():
        if f is not None:
            try:
                result = save_media_content(f.read(), seg_id)
                status = "completed" if result["status"] == "success" else "error"
                msg = "Uploaded manually" if status == "completed" else result["message"]
                st.session_state.aroll_status[seg_id] = {"status": status, "message": msg, "local_path": result.get("file_path", ""), "manually_uploaded": True, "timestamp": time.time()}
            except Exception as e:
                st.session_state.aroll_status[seg_id] = {"status": "error", "message": str(e), "manually_uploaded": True, "timestamp": time.time()}
        save_aroll_status()


# ── main UI ────────────────────────────────────────────────────────────────
def main():
    load_script_data()
    load_aroll_status()

    render_step_header("5A A-Roll Video Production", "Generate presenter video")

    if not st.session_state.segments:
        st.warning("No A-Roll segments found. Please create them in Script Segmentation.")
        st.stop()

    aroll_segments = st.session_state.segments
    heygen_ok = config_manager.config.is_heygen_configured()

    if not heygen_ok:
        st.info("HeyGen is not configured. A-Roll videos will be generated using Edge-TTS (audio only). Configure HEYGEN_API_KEY to enable avatar video generation.")

    with st.expander("A-Roll Settings", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            prev_key = os.environ.get("HEYGEN_API_KEY", "")
            new_key = st.text_input("HeyGen API Key", type="password", value=prev_key, key="heygen_api_key_input")
            if new_key != prev_key and new_key:
                os.environ["HEYGEN_API_KEY"] = new_key
                st.success("API key saved for this session")
        with col2:
            manual_upload = st.checkbox("Enable manual upload", value=st.session_state.manual_upload)
            st.session_state.manual_upload = manual_upload

        if not manual_upload and heygen_ok:
            avatar_type_label = st.radio("Avatar Type", ["Video Avatar", "Photo Avatar"], horizontal=True)
            st.session_state.avatar_type = "video" if avatar_type_label == "Video Avatar" else "photo"

            col1, col2 = st.columns(2)
            with col1:
                if st.session_state.avatar_type == "video":
                    avatar_opts = {"Abigail (Female)": "Abigail_expressive_2024112501", "Arthur (Male)": "Arthur_expressive_2024112501"}
                    sel = st.selectbox("Video Avatar", list(avatar_opts.keys()))
                    st.session_state.heygen_avatar_id = avatar_opts[sel]
                else:
                    pid = st.text_input("Photo Avatar ID", value=st.session_state.heygen_photo_avatar_id)
                    st.session_state.heygen_photo_avatar_id = pid
            with col2:
                voice_opts = {"Arthur (Male)": "fe612bdf07a94d5fa7b80bf1282937d1", "Matt (Male)": "9f8ff4eed26442168a8f2dc03c56e9ce", "Sarah (Female)": "1582f2abbc114670b8999f22af70f09d"}
                sel_v = st.selectbox("Voice", list(voice_opts.keys()))
                st.session_state.heygen_voice_id = voice_opts[sel_v]

    tab1, tab2 = st.tabs(["A-Roll Segments", "Segment IDs"])

    with tab1:
        st.subheader("A-Roll Segments")
        for i, segment in enumerate(aroll_segments):
            seg_id = segment.get("id", f"segment_{i}")
            text = segment.get("content", "").strip()
            seg_status = st.session_state.aroll_status.get(seg_id, {})
            status = seg_status.get("status", "not_started")
            message = seg_status.get("message", "Not started yet")
            color = {"completed": "green", "ready": "green", "success": "green", "done": "green", "error": "red", "processing": "blue", "submitted": "orange"}.get(status.lower(), "gray")

            with st.expander(f"Segment {i+1}: {seg_id}", expanded=True):
                st.markdown(f"**Text:** {text}")
                st.markdown(f"**Status:** <span style='color:{color}'>{status}</span> — {message}", unsafe_allow_html=True)
                if manual_upload:
                    up = st.file_uploader(f"Upload video for {seg_id}", type=["mp4", "mov"], key=f"upload_{seg_id}")
                    if up:
                        st.session_state.uploaded_files[seg_id] = up
                local_path = seg_status.get("local_path")
                if local_path and Path(local_path).exists():
                    st.video(local_path)
                elif seg_status.get("video_url"):
                    st.markdown(f"**HeyGen URL:** [View Video]({seg_status['video_url']})")

    with tab2:
        id_tab1, id_tab2 = st.tabs(["Current IDs", "Manual ID Entry"])
        with id_tab1:
            id_data = [{"Segment": f"Segment {i+1}", "ID": s.get("id", f"segment_{i}"), "Content": s.get("content", "")[:50] + "…", "HeyGen ID": st.session_state.aroll_fetch_ids.get(s.get("id", ""), "")} for i, s in enumerate(aroll_segments)]
            st.table(id_data)

        with id_tab2:
            manual_ids = {}
            for i, seg in enumerate(aroll_segments):
                seg_id = seg.get("id", f"segment_{i}")
                c1, c2 = st.columns([3, 2])
                c1.markdown(f"**Segment {i+1}:** {seg.get('content', '')[:30]}…")
                mid = c2.text_input(f"ID for Segment {i+1}", value=st.session_state.manual_ids.get(seg_id, ""), key=f"manual_id_{seg_id}")
                manual_ids[seg_id] = mid
            st.session_state.manual_ids = manual_ids

            if st.button("Fetch Content from Manual IDs", type="primary"):
                valid = {k: v for k, v in manual_ids.items() if v}
                if not valid:
                    st.warning("No valid IDs entered.")
                else:
                    with st.spinner(f"Fetching {len(valid)} IDs…"):
                        r = manual_fetch_content(valid)
                    if r["status"] == "success":
                        st.success(f"Fetched {r['checked']}, downloaded {r['completed']}")
                    else:
                        st.error(r.get("message", "Unknown error"))
                    st.rerun()

    # ── action buttons ──────────────────────────────────────────────────────
    st.subheader("Actions")
    col1, col2, col3 = st.columns(3)

    with col1:
        if manual_upload and st.session_state.uploaded_files:
            if st.button("Process Uploaded Files", type="primary"):
                with st.spinner("Processing…"):
                    handle_manual_uploads(st.session_state.uploaded_files)
                st.success("Files processed!")
                st.rerun()
        elif not manual_upload:
            if st.button("Generate A-Roll Videos", type="primary"):
                with st.spinner("Generating…"):
                    r = generate_aroll_content(aroll_segments, st.session_state.avatar_type)
                if r["status"] == "success":
                    st.success(f"Submitted {r['generated']} videos")
                else:
                    st.error(r.get("message", "Unknown error"))
                if r.get("errors"):
                    st.error(f"Errors: {r['errors']}")
                st.rerun()

    with col2:
        if st.button("Check Status"):
            if not manual_upload and heygen_ok:
                with st.spinner("Checking…"):
                    r = check_aroll_status_from_heygen()
                st.success(f"Checked {r['checked']}, completed {r['completed']}")
            else:
                st.info("Manual upload mode or HeyGen not configured: no status to check")
            st.rerun()

    with col3:
        if st.button("Mark Step Complete"):
            all_done = all(
                st.session_state.aroll_status.get(s.get("id", ""), {}).get("status", "").lower() in {"completed", "ready", "success", "done"}
                for s in aroll_segments
            )
            if all_done:
                mark_step_complete("aroll_production")
                st.success("A-Roll production complete!")
            else:
                st.warning("Not all A-Roll videos are complete yet.")

    st.markdown("---")
    render_step_navigation(current_step=5, prev_step_path="pages/4_BRoll_Prompts.py", next_step_path="pages/5B_BRoll_Video_Production.py")


if __name__ == "__main__":
    main()
