import streamlit as st
import os
import sys
import json
from pathlib import Path

# Add app root to path
_app_root = Path(__file__).parent.parent.absolute()
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

try:
    from components.custom_navigation import render_custom_sidebar, render_horizontal_navigation, render_step_navigation
    from components.progress import render_step_header
    from utils.session_state import get_settings, get_project_path, mark_step_complete
    from utils.video.broll_defaults import apply_default_broll_ids, update_session_state_with_defaults
except ImportError as e:
    st.error(f"Failed to import local modules: {e}")
    st.stop()

from app.core.logging import get_logger
from app.services.video_assembly_service import video_assembly_service
from app.core.models import ProgressEvent

logger = get_logger("pages.6")

st.set_page_config(
    page_title="Video Assembly | ReelForge",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color:white !important; }
    [data-testid="stSidebar"] * { color:black !important; }
    [data-testid="stSidebar"] button { background-color:#e6f2ff !important; color:#0066cc !important; border-radius:6px !important; }
    .horizontal-nav { margin-bottom:20px; padding:10px; background-color:#f0f2f6; border-radius:10px; }
</style>
""", unsafe_allow_html=True)

def load_css():
    css_file = Path("assets/css/style.css")
    if css_file.exists():
        st.markdown(f"<style>{css_file.read_text()}</style>", unsafe_allow_html=True)

load_css()

st.markdown("<div class='horizontal-nav'>", unsafe_allow_html=True)
render_horizontal_navigation()
st.markdown("</div>", unsafe_allow_html=True)
render_custom_sidebar()

settings = get_settings()
project_path = get_project_path()

# ── session state ──────────────────────────────────────────────────────────
if "video_assembly" not in st.session_state:
    st.session_state.video_assembly = {"status": "not_started", "progress": 0, "output_path": None, "error": None, "sequence": []}
if "content_status" not in st.session_state:
    st.session_state.content_status = {"aroll": {}, "broll": {}}

# ── helpers ────────────────────────────────────────────────────────────────
def load_content_status() -> dict:
    result = {"aroll": {}, "broll": {}}

    broll_file = project_path / "content_status.json"
    if broll_file.exists():
        try:
            data = json.loads(broll_file.read_text())
            result["broll"] = data.get("broll", {})
            result["aroll"] = data.get("aroll", {})
        except Exception as e:
            logger.error(f"Error loading content_status.json: {e}")

    # Supplement aroll from dedicated status file
    aroll_file = project_path / "aroll_status.json"
    if aroll_file.exists() and not result["aroll"]:
        try:
            result["aroll"] = json.loads(aroll_file.read_text())
        except Exception as e:
            logger.error(f"Error loading aroll_status.json: {e}")

    st.session_state.content_status = result
    logger.info(f"Content status: {len(result['aroll'])} A-Roll, {len(result['broll'])} B-Roll segments")
    return result


def load_segments() -> list:
    script_file = project_path / "script.json"
    if not script_file.exists():
        st.error("Script file not found. Please complete Script Segmentation first.")
        return []
    try:
        return json.loads(script_file.read_text()).get("segments", [])
    except Exception as e:
        st.error(f"Error loading segments: {e}")
        return []


def get_aroll_filepath(segment_id: str) -> str | None:
    aroll_status = st.session_state.content_status.get("aroll", {}).get(segment_id, {})
    lp = aroll_status.get("local_path")
    if lp and Path(lp).exists():
        return lp

    for candidate in [
        project_path / "media" / "a-roll" / f"{segment_id}.mp4",
        project_path / "media" / "aroll" / f"{segment_id}.mp4",
        _app_root / "media" / "a-roll" / f"{segment_id}.mp4",
    ]:
        if candidate.exists():
            return str(candidate)
    logger.warning(f"A-Roll file not found for {segment_id}")
    return None


def get_broll_filepath(segment_id: str) -> str | None:
    seg_data = st.session_state.content_status.get("broll", {}).get(segment_id, {})
    fp = seg_data.get("file_path")
    if fp and Path(fp).exists():
        return fp

    seg_num = segment_id.split("_")[-1]
    for ext in [".mp4", ".mov", ".png", ".jpg"]:
        for pattern in [
            project_path / "media" / "b-roll" / f"broll_segment_{seg_num}{ext}",
            project_path / "media" / "b-roll" / f"{segment_id}{ext}",
            _app_root / "media" / "b-roll" / f"broll_segment_{seg_num}{ext}",
        ]:
            if pattern.exists():
                return str(pattern)
    logger.warning(f"B-Roll file not found for {segment_id}")
    return None


# ── sequence building ──────────────────────────────────────────────────────
_SEQUENCE_OPTIONS = [
    "Standard (A-Roll start, B-Roll middle with A-Roll audio, A-Roll end)",
    "A-Roll Bookends (A-Roll at start and end only, B-Roll middle)",
    "A-Roll Sandwich (A-Roll at start, middle, and end)",
    "B-Roll Heavy (Only first segment uses A-Roll visual)",
    "B-Roll Full (All B-Roll visuals with A-Roll audio)",
    "Custom (Manual Arrangement)",
]


def build_sequence(pattern: str, aroll_status: dict, broll_status: dict) -> list[dict]:
    n_a = len(aroll_status)
    n_b = max(len(broll_status), 1)
    sequence = []

    def _aroll(idx: int) -> dict | None:
        sid = f"segment_{idx}"
        p = get_aroll_filepath(sid)
        if p:
            return {"type": "aroll_full", "aroll_path": p, "broll_path": None, "segment_id": sid}
        return None

    def _broll(a_idx: int, b_idx: int) -> dict | None:
        a_sid = f"segment_{a_idx}"
        b_sid = f"segment_{b_idx % n_b}"
        ap = get_aroll_filepath(a_sid)
        bp = get_broll_filepath(b_sid)
        if ap and bp:
            return {"type": "broll_with_aroll_audio", "aroll_path": ap, "broll_path": bp, "segment_id": a_sid, "broll_id": b_sid}
        return None

    if "B-Roll Full" in pattern:
        for i in range(n_a):
            item = _broll(i, i)
            if item:
                sequence.append(item)
    elif "Bookends" in pattern:
        if (item := _aroll(0)):
            sequence.append(item)
        for i in range(1, n_a - 1):
            if (item := _broll(i, i - 1)):
                sequence.append(item)
        if n_a > 1 and (item := _aroll(n_a - 1)):
            sequence.append(item)
    elif "Sandwich" in pattern:
        positions = {0, n_a // 2, n_a - 1}
        for i in range(n_a):
            item = _aroll(i) if i in positions else _broll(i, i - 1)
            if item:
                sequence.append(item)
    elif "B-Roll Heavy" in pattern:
        if (item := _aroll(0)):
            sequence.append(item)
        for i in range(1, n_a):
            if (item := _broll(i, i - 1)):
                sequence.append(item)
    else:  # Standard
        if (item := _aroll(0)):
            sequence.append(item)
        for i in range(1, n_a - 1):
            if (item := _broll(i, i - 1)):
                sequence.append(item)
        if n_a > 1 and (item := _aroll(n_a - 1)):
            sequence.append(item)

    return sequence


# ── main UI ────────────────────────────────────────────────────────────────
render_step_header(6, "Video Assembly", 8)
st.title("🎬 Video Assembly")
st.markdown("Combine A-Roll and B-Roll into a complete short-form video.")
st.info("Images (PNG/JPG) as B-Roll are supported — they will be held for the duration of the A-Roll audio.")

content_status = load_content_status()
segments = load_segments()

# Apply default B-roll IDs
if apply_default_broll_ids(st.session_state.content_status):
    update_session_state_with_defaults(st.session_state)

aroll_segs = [s for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
broll_segs = [s for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll"]

# Content summary
st.subheader("Content Summary")
c1, c2 = st.columns(2)
aroll_done = sum(1 for i in range(len(aroll_segs)) if content_status["aroll"].get(f"segment_{i}", {}).get("status") in {"completed", "complete", "ready", "success", "done"})
broll_done = sum(1 for i in range(len(broll_segs)) if content_status["broll"].get(f"segment_{i}", {}).get("status") in {"complete", "completed", "success"})
c1.info(f"A-Roll: {aroll_done}/{len(aroll_segs)} ready")
c2.info(f"B-Roll: {broll_done}/{len(broll_segs)} ready")

# ── Sequence options ──────────────────────────────────────────────────────
st.subheader("Assembly Options")
selected_seq = st.selectbox("Sequence Pattern:", _SEQUENCE_OPTIONS, key="sequence_selectbox")

resolution_map = {"1080×1920 (9:16)": (1080, 1920), "720×1280 (9:16)": (720, 1280), "1920×1080 (16:9)": (1920, 1080)}
sel_res = st.selectbox("Output Resolution:", list(resolution_map.keys()))
width, height = resolution_map[sel_res]

# Regenerate sequence when pattern changes (non-custom)
if "Custom" not in selected_seq:
    aroll_status = content_status.get("aroll", {})
    broll_status = content_status.get("broll", {})
    if aroll_status:
        seq = build_sequence(selected_seq, aroll_status, broll_status)
        st.session_state.video_assembly["sequence"] = seq

# ── Custom sequence editor ────────────────────────────────────────────────
if "Custom" in selected_seq:
    st.markdown("### Custom Sequence Editor")
    if "manual_sequence" not in st.session_state:
        st.session_state.manual_sequence = list(st.session_state.video_assembly.get("sequence", []))

    manual_seq = st.session_state.manual_sequence

    a_segs_avail = [f"segment_{i}" for i in range(len(aroll_segs)) if get_aroll_filepath(f"segment_{i}")]
    b_segs_avail = [f"segment_{i}" for i in range(len(broll_segs)) if get_broll_filepath(f"segment_{i}")]

    ec1, ec2 = st.columns([1, 3])

    with ec1:
        st.markdown("**Add A-Roll**")
        for sid in a_segs_avail:
            if st.button(f"+ {sid}", key=f"add_a_{sid}"):
                manual_seq.append({"type": "aroll_full", "aroll_path": get_aroll_filepath(sid), "broll_path": None, "segment_id": sid})
                st.rerun()
        st.markdown("**Add B-Roll**")
        for bsid in b_segs_avail:
            a_choice = st.selectbox(f"Audio for {bsid}", a_segs_avail, key=f"audio_for_{bsid}")
            if st.button(f"+ {bsid}", key=f"add_b_{bsid}"):
                manual_seq.append({"type": "broll_with_aroll_audio", "aroll_path": get_aroll_filepath(a_choice), "broll_path": get_broll_filepath(bsid), "segment_id": a_choice, "broll_id": bsid})
                st.rerun()

    with ec2:
        st.markdown("**Current Sequence**")
        for i, item in enumerate(list(manual_seq)):
            cols = st.columns([3, 1, 1, 1])
            if item["type"] == "aroll_full":
                cols[0].markdown(f"**A-Roll** {item['segment_id']}")
            else:
                cols[0].markdown(f"**B-Roll** {item.get('broll_id','')} + audio {item['segment_id']}")
            if i > 0 and cols[1].button("↑", key=f"up_{i}"):
                manual_seq[i], manual_seq[i - 1] = manual_seq[i - 1], manual_seq[i]
                st.rerun()
            if i < len(manual_seq) - 1 and cols[2].button("↓", key=f"dn_{i}"):
                manual_seq[i], manual_seq[i + 1] = manual_seq[i + 1], manual_seq[i]
                st.rerun()
            if cols[3].button("✖", key=f"rm_{i}"):
                manual_seq.pop(i)
                st.rerun()

    if st.button("Apply Custom Sequence", type="primary"):
        st.session_state.video_assembly["sequence"] = list(manual_seq)
        st.success("Custom sequence applied!")
        st.rerun()

# ── Sequence preview ──────────────────────────────────────────────────────
sequence = st.session_state.video_assembly.get("sequence", [])
if sequence:
    st.markdown("#### Sequence Preview")
    cols = st.columns(min(8, len(sequence)))
    for item, col in zip(sequence, cols):
        if item["type"] == "aroll_full":
            n = item["segment_id"].split("_")[-1]
            col.markdown(f"<div style='border:2px solid #4CAF50;padding:6px;border-radius:5px;background:#E8F5E9;text-align:center'><b>A-{int(n)+1}</b><br><small>A-Roll</small></div>", unsafe_allow_html=True)
        else:
            bn = item.get("broll_id", "").split("_")[-1]
            an = item["segment_id"].split("_")[-1]
            col.markdown(f"<div style='border:2px solid #2196F3;padding:6px;border-radius:5px;background:#E3F2FD;text-align:center'><b>B-{int(bn)+1}+A-{int(an)+1}</b><br><small>B-Roll</small></div>", unsafe_allow_html=True)

# ── Assemble button ───────────────────────────────────────────────────────
st.markdown("---")
if st.button("🎬 Assemble Video", type="primary", use_container_width=True):
    if not sequence:
        st.error("No sequence defined. Please select a pattern or create a custom arrangement.")
    else:
        progress_bar = st.progress(0)
        status_text = st.empty()

        def _progress_cb(event: ProgressEvent) -> None:
            progress_bar.progress(min(1.0, event.progress))
            status_text.text(event.message)

        with st.spinner("Assembling video…"):
            try:
                asset = video_assembly_service.assemble(
                    sequence=sequence,
                    target_resolution=(width, height),
                    output_dir=project_path / "output",
                    progress_cb=_progress_cb,
                )
                st.session_state.video_assembly["status"] = "complete"
                st.session_state.video_assembly["output_path"] = asset.file_path
                mark_step_complete("video_assembly")
                st.success("Video assembled successfully!")
            except Exception as e:
                logger.error(f"Assembly error: {e}")
                st.session_state.video_assembly["status"] = "error"
                st.session_state.video_assembly["error"] = str(e)
                st.error(f"Assembly failed: {e}")
        st.rerun()

# ── Output preview ────────────────────────────────────────────────────────
if st.session_state.video_assembly.get("status") == "complete":
    out = st.session_state.video_assembly.get("output_path")
    if out and Path(out).exists():
        st.subheader("Output Video")
        st.video(out)
        with open(out, "rb") as f:
            st.download_button("📥 Download Video", data=f, file_name=Path(out).name, mime="video/mp4")
    else:
        st.warning("Output file not found.")

st.markdown("---")
render_step_navigation(
    current_step=7,
    prev_step_path="pages/5B_BRoll_Video_Production.py",
    next_step_path="pages/7_Caption_The_Dreams.py",
)
