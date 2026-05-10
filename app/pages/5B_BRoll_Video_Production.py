import streamlit as st
import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

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
from app.services.comfyui_service import comfyui_service
from app.services.replicate_service import replicate_service
from app.services.frame_html import frame_renderer
from app.services.workflows import resolve, list_all

logger = get_logger("pages.5b")

st.set_page_config(
    page_title="B-Roll Video Production | ReelForge",
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
    "broll_prompts": {},
    "content_status": {"broll": {}, "aroll": {}},
    "manual_upload": False,
    "uploaded_files": {},
    "batch_process_status": {"submitted": False, "prompt_ids": {}, "errors": {}},
}
for k, v in _defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# ── helpers ────────────────────────────────────────────────────────────────
def _content_status_path() -> Path:
    return project_path / "content_status.json"


def load_script_data() -> bool:
    script_file = project_path / "script.json"
    if not script_file.exists():
        logger.warning(f"Script file not found: {script_file}")
        return False
    try:
        data = json.loads(script_file.read_text())
        segs = [s for s in data.get("segments", []) if isinstance(s, dict) and s.get("type") == "B-Roll"]
        if segs:
            st.session_state.segments = segs
            logger.info(f"Loaded {len(segs)} B-Roll segments")
            return True
        logger.warning("No valid B-Roll segments found in script.json")
        return False
    except json.JSONDecodeError:
        logger.error("Failed to parse script.json")
        return False


def load_broll_prompts() -> bool:
    for candidate in [
        project_path / "broll_prompts.json",
        Path("config/user_data/my_short_video/broll_prompts.json"),
    ]:
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text())
                if not isinstance(data, dict):
                    continue
                if "prompts" in data:
                    prompts_data = data["prompts"]
                else:
                    prompts_data = {k: v for k, v in data.items() if isinstance(v, dict) and "prompt" in v}
                    data = {"prompts": prompts_data, "broll_type": "video"}
                if prompts_data:
                    st.session_state.broll_prompts = data
                    logger.info(f"Loaded {len(prompts_data)} B-Roll prompts from {candidate}")
                    return True
            except Exception as e:
                logger.error(f"Error loading prompts from {candidate}: {e}")
    logger.warning("B-Roll prompts not found in any location")
    return False


def load_content_status() -> dict:
    p = _content_status_path()
    if p.exists():
        try:
            data = json.loads(p.read_text())
            st.session_state.content_status = data
            return data
        except Exception as e:
            logger.error(f"Error loading content status: {e}")
    return st.session_state.content_status


def save_content_status() -> None:
    try:
        _content_status_path().write_text(json.dumps(st.session_state.content_status, indent=2))
    except IOError as e:
        logger.error(f"Error saving content status: {e}")


def update_content_status(segment_id: str, segment_type: str, status: str, message: str = "", **extra) -> None:
    if segment_type not in st.session_state.content_status:
        st.session_state.content_status[segment_type] = {}
    entry = {"status": status, "message": message, "timestamp": time.time()}
    entry.update(extra)
    st.session_state.content_status[segment_type][segment_id] = entry
    save_content_status()


# ── B-Roll generation backends ─────────────────────────────────────────────
def _get_broll_prompts_dict() -> dict:
    raw = st.session_state.broll_prompts
    if "prompts" in raw:
        return raw["prompts"]
    return raw


def generate_broll_comfyui(segments: list, workflow_name: str) -> dict:
    prompts = _get_broll_prompts_dict()
    generated, errors = 0, {}
    output_dir = project_path / "media" / "b-roll"
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, seg in enumerate(segments):
        seg_id = f"segment_{i}"
        prompt_data = prompts.get(seg_id, {})
        prompt = prompt_data.get("prompt", seg.get("content", ""))
        if not prompt:
            logger.warning(f"No prompt for {seg_id}, skipping")
            continue

        update_content_status(seg_id, "broll", "processing", "Submitting to ComfyUI…")
        try:
            asset = comfyui_service.generate_image(
                prompt=prompt,
                workflow_name=workflow_name,
                output_dir=output_dir,
                segment_id=seg_id,
            )
            update_content_status(seg_id, "broll", "complete", "Done via ComfyUI", file_path=asset.file_path)
            logger.info(f"ComfyUI done for {seg_id}: {asset.file_path}")
            generated += 1
        except Exception as e:
            logger.error(f"ComfyUI failed for {seg_id}: {e}")
            update_content_status(seg_id, "broll", "error", str(e))
            errors[seg_id] = str(e)

    return {"status": "success" if not errors else "partial", "generated": generated, "errors": errors}


def generate_broll_replicate(segments: list, model_key: str) -> dict:
    prompts = _get_broll_prompts_dict()
    generated, errors = 0, {}
    output_dir = project_path / "media" / "b-roll"
    output_dir.mkdir(parents=True, exist_ok=True)

    for i, seg in enumerate(segments):
        seg_id = f"segment_{i}"
        prompt_data = prompts.get(seg_id, {})
        prompt = prompt_data.get("prompt", seg.get("content", ""))
        if not prompt:
            continue

        update_content_status(seg_id, "broll", "processing", "Submitting to Replicate…")
        try:
            asset = replicate_service.generate_video(
                prompt=prompt,
                model_key=model_key,
                output_dir=output_dir,
                segment_id=seg_id,
            )
            update_content_status(seg_id, "broll", "complete", "Done via Replicate", file_path=asset.file_path)
            generated += 1
        except Exception as e:
            logger.error(f"Replicate failed for {seg_id}: {e}")
            update_content_status(seg_id, "broll", "error", str(e))
            errors[seg_id] = str(e)

    return {"status": "success" if not errors else "partial", "generated": generated, "errors": errors}


def generate_broll_html_template(segments: list, template_name: str) -> dict:
    prompts = _get_broll_prompts_dict()
    generated, errors = 0, {}
    output_dir = project_path / "media" / "b-roll"
    output_dir.mkdir(parents=True, exist_ok=True)

    templates = frame_renderer.list_templates()
    template_path = template_name if template_name in templates else (templates[0] if templates else "")

    for i, seg in enumerate(segments):
        seg_id = f"segment_{i}"
        prompt_data = prompts.get(seg_id, {})
        text = prompt_data.get("prompt", seg.get("content", ""))
        out_path = str(output_dir / f"{seg_id}.png")

        update_content_status(seg_id, "broll", "processing", "Rendering HTML frame…")
        try:
            asset = frame_renderer.render_sync(
                template_path=template_path,
                title=f"Segment {i+1}",
                text=text,
                output_path=out_path,
            )
            update_content_status(seg_id, "broll", "complete", "Done via HTML template", file_path=asset.file_path)
            generated += 1
        except Exception as e:
            logger.error(f"Frame render failed for {seg_id}: {e}")
            update_content_status(seg_id, "broll", "error", str(e))
            errors[seg_id] = str(e)

    return {"status": "success" if not errors else "partial", "generated": generated, "errors": errors}


def handle_manual_uploads(uploaded_files: dict) -> None:
    output_dir = project_path / "media" / "b-roll"
    output_dir.mkdir(parents=True, exist_ok=True)
    for seg_id, f in uploaded_files.items():
        if f is not None:
            try:
                ext = Path(f.name).suffix
                out_path = str(output_dir / f"{seg_id}{ext}")
                Path(out_path).write_bytes(f.read())
                update_content_status(seg_id, "broll", "complete", "Manual upload", file_path=out_path)
                logger.info(f"Manual upload saved: {out_path}")
            except Exception as e:
                logger.error(f"Manual upload failed for {seg_id}: {e}")
                update_content_status(seg_id, "broll", "error", str(e))


# ── main UI ────────────────────────────────────────────────────────────────
render_step_header("5B B-Roll Video Production", "Generate B-Roll visual content")

st.title("⚡ B-Roll Content Production")
st.markdown("Generate visual B-Roll content using ComfyUI, Replicate, or HTML templates.")

# Load data
has_script = load_script_data()
has_prompts = load_broll_prompts()
load_content_status()

if not has_script:
    st.error("No B-Roll segments found. Please complete Script Segmentation (Step 3) first.")
    if st.button("Go to Script Segmentation"):
        st.switch_page("pages/3_Script_Segmentation.py")
    st.stop()

if not has_prompts:
    st.error("No B-Roll prompts found. Please complete B-Roll Prompts (Step 4) first.")
    if st.button("Go to B-Roll Prompts"):
        st.switch_page("pages/4_BRoll_Prompts.py")
    st.stop()

broll_segments = st.session_state.segments

# ── Backend selection ──────────────────────────────────────────────────────
st.subheader("Production Backend")
backend = st.radio(
    "Choose B-Roll generation backend:",
    ["ComfyUI (Local AI)", "Replicate (Cloud AI)", "HTML Template (Instant)", "Manual Upload"],
    horizontal=True,
    help="ComfyUI and Replicate generate AI images/videos. HTML templates render instantly as static frames.",
)

backend_config = {}

if backend == "ComfyUI (Local AI)":
    available_workflows = list_all()
    if available_workflows:
        wf = st.selectbox("Workflow", available_workflows, help="Workflow JSON files from the app/workflows/ directory")
        backend_config["workflow_name"] = wf
    else:
        st.warning("No workflow files found in app/workflows/. ComfyUI generation requires a workflow JSON.")
    st.info(f"ComfyUI Image API: {config_manager.config.comfyui_image_api_url}")

elif backend == "Replicate (Cloud AI)":
    if not config_manager.config.is_replicate_configured():
        st.warning("REPLICATE_API_TOKEN is not set. Configure it in .env or the Settings page.")
    model_opts = {"WAN 2.1 T2V 480p": "wan_2_1_t2v_480p", "Kling V2.0": "kling_v2", "Hunyuan Video": "hunyuan_video", "Zeroscope V2": "zeroscope_v2"}
    sel_model = st.selectbox("Model", list(model_opts.keys()))
    backend_config["model_key"] = model_opts[sel_model]

elif backend == "HTML Template (Instant)":
    templates = frame_renderer.list_templates()
    if templates:
        sel_tpl = st.selectbox("Template", templates)
        backend_config["template_name"] = sel_tpl
    else:
        st.info("No HTML templates found. A plain text-on-black frame will be rendered for each segment.")
        backend_config["template_name"] = ""

# ── Segment overview ──────────────────────────────────────────────────────
st.markdown("---")
st.subheader("B-Roll Segments")
prompts_dict = _get_broll_prompts_dict()

for i, seg in enumerate(broll_segments):
    seg_id = f"segment_{i}"
    seg_status = st.session_state.content_status.get("broll", {}).get(seg_id, {})
    status = seg_status.get("status", "not_started")
    message = seg_status.get("message", "Not started")
    color = {"complete": "green", "error": "red", "processing": "blue"}.get(status, "gray")
    prompt_text = prompts_dict.get(seg_id, {}).get("prompt", seg.get("content", ""))[:100]

    with st.expander(f"Segment {i+1} ({seg_id})", expanded=(i == 0)):
        st.markdown(f"**Prompt:** {prompt_text}…")
        st.markdown(f"**Status:** <span style='color:{color}'>{status}</span> — {message}", unsafe_allow_html=True)

        if backend == "Manual Upload":
            up = st.file_uploader(f"Upload B-Roll for {seg_id}", type=["mp4", "mov", "png", "jpg"], key=f"broll_up_{seg_id}")
            if up:
                if "uploaded_files" not in st.session_state:
                    st.session_state.uploaded_files = {}
                st.session_state.uploaded_files[seg_id] = up

        file_path = seg_status.get("file_path")
        if file_path and Path(file_path).exists():
            if file_path.endswith((".mp4", ".mov")):
                st.video(file_path)
            else:
                st.image(file_path, use_column_width=True)

# ── Generate button ────────────────────────────────────────────────────────
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if backend == "Manual Upload":
        if st.button("Process Uploaded Files", type="primary"):
            handle_manual_uploads(st.session_state.get("uploaded_files", {}))
            st.success("Files processed!")
            st.rerun()
    else:
        lbl = {"ComfyUI (Local AI)": "Generate via ComfyUI", "Replicate (Cloud AI)": "Generate via Replicate", "HTML Template (Instant)": "Render HTML Frames"}.get(backend, "Generate")
        if st.button(lbl, type="primary"):
            with st.spinner(f"Running {backend}…"):
                if backend == "ComfyUI (Local AI)":
                    r = generate_broll_comfyui(broll_segments, backend_config.get("workflow_name", "image_homepc"))
                elif backend == "Replicate (Cloud AI)":
                    r = generate_broll_replicate(broll_segments, backend_config.get("model_key", "wan_2_1_t2v_480p"))
                else:
                    r = generate_broll_html_template(broll_segments, backend_config.get("template_name", ""))
            if r.get("generated", 0) > 0:
                st.success(f"Generated {r['generated']} B-Roll segments!")
            if r.get("errors"):
                st.error(f"Errors: {r['errors']}")
            st.rerun()

with col2:
    if st.button("Mark Step Complete"):
        all_done = all(
            st.session_state.content_status.get("broll", {}).get(f"segment_{i}", {}).get("status") == "complete"
            for i in range(len(broll_segments))
        )
        if all_done:
            mark_step_complete("broll_production")
            st.success("B-Roll production complete!")
        else:
            st.warning("Not all B-Roll segments are complete.")

st.markdown("---")
render_step_navigation(
    current_step=5,
    prev_step_path="pages/5A_ARoll_Video_Production.py",
    next_step_path="pages/6_Video_Assembly.py",
)
