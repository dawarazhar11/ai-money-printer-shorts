#!/usr/bin/env python3
"""Page for adding animated word-by-word captions to videos."""
import os
import sys
import traceback
from pathlib import Path

import streamlit as st

# Add app root to path
_app_root = Path(__file__).parent.parent.absolute()
if str(_app_root) not in sys.path:
    sys.path.insert(0, str(_app_root))

try:
    from components.progress import render_step_header
    from utils.session_state import mark_step_complete
    from components.navigation import render_workflow_navigation, render_step_navigation
    from utils.video.captions import check_dependencies, get_available_caption_styles, CAPTION_STYLES
    from utils.audio.transcription import get_available_engines
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.stop()

from app.core.logging import get_logger
from app.services.caption_service import caption_service, list_effects

logger = get_logger("pages.7")

st.set_page_config(page_title="Captioning | ReelForge", page_icon="✨", layout="wide")

# ── session state ──────────────────────────────────────────────────────────
if "caption_dreams" not in st.session_state:
    st.session_state.caption_dreams = {
        "status": "not_started",
        "source_video": None,
        "output_path": None,
        "selected_style": "tiktok",
        "model_size": "base",
        "transcription_engine": "auto",
        "animation_style": "word_by_word",
        "font_size": 50,
        "font_style": "Arial Bold",
        "text_color": "#FFFFFF",
        "stroke_width": 3,
        "stroke_color": "#000000",
        "show_textbox": True,
        "bg_opacity": 70,
        "bg_color": "#000000",
        "text_align": "center",
        "enable_multiline": True,
        "max_line_width": 80,
        "line_padding": 10,
        "position_type": "bottom",
        "vertical_pos": 80,
        "horizontal_pos": 50,
        "force_captions": False,
        "default_caption": "No speech detected",
        "error": None,
    }

_ANIMATION_STYLES = {
    "word_by_word": {"name": "Word by Word", "description": "Words appear one by one as spoken"},
    "fade_in_out": {"name": "Fade In/Out", "description": "Words fade in/out as spoken"},
    "color_highlight": {"name": "Color Highlight", "description": "Current word highlighted"},
    "single_word_focus": {"name": "Single Word Focus", "description": "Only current word shown"},
}

_FONT_OPTIONS = ["Default", "Arial", "Arial Bold", "Impact", "Georgia", "Times New Roman",
                  "Courier New", "Verdana", "Pacifico", "Dancing Script", "Lobster"]

_FONT_FILE_MAP = {
    "Default": "Arial.ttf", "Arial": "Arial.ttf", "Arial Bold": "Arial Bold.ttf",
    "Impact": "Impact.ttf", "Georgia": "Georgia.ttf", "Times New Roman": "Times New Roman.ttf",
    "Courier New": "Courier New.ttf", "Verdana": "Verdana.ttf", "Pacifico": "Pacifico-Regular.ttf",
    "Dancing Script": "DancingScript-Regular.ttf", "Lobster": "Lobster-Regular.ttf",
}


def _get_font_path(font_name: str) -> str:
    return _FONT_FILE_MAP.get(font_name, "Arial.ttf")


# ── page layout ────────────────────────────────────────────────────────────
render_step_header("Caption The Dreams", "Add animated word-by-word captions to your video")
render_workflow_navigation()

st.markdown("# ✨ Caption The Dreams")
st.markdown("Add beautiful animated captions that map each word precisely to the spoken audio.")

dep_check = check_dependencies()
if not dep_check.get("all_available"):
    st.error(f"Missing dependencies: {', '.join(dep_check.get('missing', []))}")
    st.info("Please install the required dependencies to use this feature.")
    st.stop()

# ── Step 1: Select video ───────────────────────────────────────────────────
st.markdown("## Step 1: Select the Video")
video_source = st.radio("Video Source:", ["Use Assembled Video", "Upload Custom Video"], key="video_source")

if video_source == "Use Assembled Video":
    asm_path = st.session_state.get("video_assembly", {}).get("output_path")
    if asm_path and Path(asm_path).exists():
        st.session_state.caption_dreams["source_video"] = asm_path
        st.success(f"Using assembled video: {Path(asm_path).name}")
        st.video(asm_path)
    else:
        st.warning("No assembled video found. Please run Video Assembly (Step 6) first or upload a custom video.")
        st.session_state.caption_dreams["source_video"] = None
else:
    uploaded = st.file_uploader("Upload your video:", type=["mp4", "mov", "avi", "mkv"])
    if uploaded:
        os.makedirs("output", exist_ok=True)
        import time
        temp_path = os.path.join("output", f"uploaded_{int(time.time())}.mp4")
        try:
            Path(temp_path).write_bytes(uploaded.getbuffer())
            if Path(temp_path).stat().st_size > 0:
                st.session_state.caption_dreams["source_video"] = temp_path
                st.success(f"Uploaded: {Path(temp_path).name}")
                st.video(temp_path)
            else:
                st.error("Uploaded file appears empty.")
        except Exception as e:
            st.error(f"Error saving upload: {e}")

# ── Step 2: Configure settings ─────────────────────────────────────────────
if st.session_state.caption_dreams["source_video"]:
    st.markdown("## Step 2: Configure Caption Settings")
    settings_col, preview_col = st.columns([3, 2])

    with settings_col:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Caption Base Style")
            styles = get_available_caption_styles()
            sel_style = st.selectbox(
                "Base Style:",
                list(styles.keys()),
                index=list(styles.keys()).index(st.session_state.caption_dreams.get("selected_style", "tiktok")),
                format_func=lambda x: styles.get(x, x.replace("_", " ").title()),
                key="style_select",
            )
            st.session_state.caption_dreams["selected_style"] = sel_style

            st.subheader("Word Animation Style")
            animation_styles = {k: v for k, v in _ANIMATION_STYLES.items() if k != "scale_pulse"}
            sel_anim = st.selectbox(
                "Animation Type:",
                list(animation_styles.keys()),
                index=list(animation_styles.keys()).index(st.session_state.caption_dreams.get("animation_style", "word_by_word")),
                format_func=lambda x: animation_styles[x]["name"],
                key="animation_select",
            )
            st.session_state.caption_dreams["animation_style"] = sel_anim
            st.info(animation_styles[sel_anim]["description"])

            with st.expander("Caption Customization", expanded=True):
                font_size = st.slider("Font Size:", 20, 80, st.session_state.caption_dreams.get("font_size", 50), step=2)
                st.session_state.caption_dreams["font_size"] = font_size

                force_captions = st.checkbox("Force captions if no speech detected", value=st.session_state.caption_dreams.get("force_captions", False))
                st.session_state.caption_dreams["force_captions"] = force_captions
                if force_captions:
                    dc = st.text_input("Default Caption:", value=st.session_state.caption_dreams.get("default_caption", "No speech detected"))
                    st.session_state.caption_dreams["default_caption"] = dc

                pos_type = st.radio("Caption Position:", ["Bottom", "Custom Position"], index=0 if st.session_state.caption_dreams.get("position_type", "bottom") == "bottom" else 1)
                st.session_state.caption_dreams["position_type"] = pos_type.lower().replace(" ", "_")
                if pos_type == "Custom Position":
                    vp = st.slider("Vertical Position:", 0, 100, st.session_state.caption_dreams.get("vertical_pos", 80))
                    hp = st.slider("Horizontal Position:", 0, 100, st.session_state.caption_dreams.get("horizontal_pos", 50))
                    st.session_state.caption_dreams["vertical_pos"] = vp
                    st.session_state.caption_dreams["horizontal_pos"] = hp

                ta = st.radio("Text Alignment:", ["Left", "Center", "Right"], index=1)
                st.session_state.caption_dreams["text_align"] = ta.lower()

                show_tb = st.checkbox("Show Text Box Background", value=st.session_state.caption_dreams.get("show_textbox", True))
                st.session_state.caption_dreams["show_textbox"] = show_tb
                if show_tb:
                    bg_op = st.slider("Background Opacity:", 0, 100, st.session_state.caption_dreams.get("bg_opacity", 70))
                    bg_col = st.color_picker("Background Color:", value=st.session_state.caption_dreams.get("bg_color", "#000000"))
                    st.session_state.caption_dreams["bg_opacity"] = bg_op
                    st.session_state.caption_dreams["bg_color"] = bg_col

                st.subheader("Font Styling")
                sel_font = st.selectbox("Font Style:", _FONT_OPTIONS, index=_FONT_OPTIONS.index(st.session_state.caption_dreams.get("font_style", "Arial Bold")))
                st.session_state.caption_dreams["font_style"] = sel_font
                txt_col = st.color_picker("Text Color:", value=st.session_state.caption_dreams.get("text_color", "#FFFFFF"))
                st.session_state.caption_dreams["text_color"] = txt_col
                stroke_w = st.slider("Outline Width:", 0, 5, st.session_state.caption_dreams.get("stroke_width", 3))
                st.session_state.caption_dreams["stroke_width"] = stroke_w
                if stroke_w > 0:
                    stroke_c = st.color_picker("Outline Color:", value=st.session_state.caption_dreams.get("stroke_color", "#000000"))
                    st.session_state.caption_dreams["stroke_color"] = stroke_c

                st.subheader("Layout")
                multiline = st.checkbox("Multi-line Captions", value=st.session_state.caption_dreams.get("enable_multiline", True))
                st.session_state.caption_dreams["enable_multiline"] = multiline
                max_lw = st.slider("Max Line Width %:", 40, 100, st.session_state.caption_dreams.get("max_line_width", 80))
                st.session_state.caption_dreams["max_line_width"] = max_lw

        with col2:
            st.subheader("Speech Recognition Engine")
            engines = ["auto"] + get_available_engines()
            engine = st.selectbox("Transcription Engine:", engines,
                                  index=engines.index(st.session_state.caption_dreams.get("transcription_engine", "auto")),
                                  key="engine_select")
            st.session_state.caption_dreams["transcription_engine"] = engine
            if engine in ("whisper", "faster_whisper"):
                sizes = ["tiny", "base", "small", "medium", "large"]
                msz = st.selectbox("Model Size:", sizes, index=sizes.index(st.session_state.caption_dreams.get("model_size", "base")), key="model_size_select")
                st.session_state.caption_dreams["model_size"] = msz

        # ── Generate button ────────────────────────────────────────────────
        st.markdown("## Step 3: Generate Animated Captions")
        if st.button("✨ Generate Animated Captions", key="generate_btn", use_container_width=True):
            src_video = st.session_state.caption_dreams["source_video"]
            os.makedirs("output", exist_ok=True)
            out_path = os.path.abspath(os.path.join("output", f"captioned_{Path(src_video).name}"))
            st.session_state.caption_dreams["output_path"] = out_path
            st.session_state.caption_dreams["status"] = "processing"

            progress_bar = st.progress(0)
            status_text = st.empty()

            def _progress_cb(p: float, msg: str) -> None:
                progress_bar.progress(p)
                status_text.text(msg)

            custom_style = {
                "font_size": st.session_state.caption_dreams.get("font_size", 50),
                "position": "custom" if "custom" in st.session_state.caption_dreams.get("position_type", "bottom") else "bottom",
                "vertical_pos": st.session_state.caption_dreams.get("vertical_pos", 80) / 100.0,
                "horizontal_pos": st.session_state.caption_dreams.get("horizontal_pos", 50) / 100.0,
                "align": st.session_state.caption_dreams.get("text_align", "center"),
                "show_textbox": st.session_state.caption_dreams.get("show_textbox", True),
                "textbox_opacity": st.session_state.caption_dreams.get("bg_opacity", 70) / 100.0,
                "font_color": st.session_state.caption_dreams.get("text_color", "#FFFFFF"),
                "font_path": _get_font_path(st.session_state.caption_dreams.get("font_style", "Arial Bold")),
                "stroke_width": st.session_state.caption_dreams.get("stroke_width", 3),
                "stroke_color": st.session_state.caption_dreams.get("stroke_color", "#000000"),
                "force_captions_if_no_speech": st.session_state.caption_dreams.get("force_captions", False),
                "default_caption": st.session_state.caption_dreams.get("default_caption", "No speech detected"),
                "enable_multiline": st.session_state.caption_dreams.get("enable_multiline", True),
                "max_line_width": st.session_state.caption_dreams.get("max_line_width", 80),
                "line_padding": st.session_state.caption_dreams.get("line_padding", 10),
            }
            if st.session_state.caption_dreams.get("show_textbox"):
                bg_hex = st.session_state.caption_dreams.get("bg_color", "#000000").lstrip("#")
                rgb = tuple(int(bg_hex[i:i+2], 16) for i in (0, 2, 4))
                opacity = int(255 * st.session_state.caption_dreams.get("bg_opacity", 70) / 100.0)
                custom_style["highlight_color"] = rgb + (opacity,)

            logger.info(f"Starting caption generation: style={st.session_state.caption_dreams.get('selected_style')} animation={st.session_state.caption_dreams.get('animation_style')}")

            try:
                asset = caption_service.add_captions(
                    video_path=src_video,
                    output_path=out_path,
                    style_name=st.session_state.caption_dreams.get("selected_style", "tiktok"),
                    animation_style=st.session_state.caption_dreams.get("animation_style", "word_by_word"),
                    model_size=st.session_state.caption_dreams.get("model_size", "base"),
                    transcription_engine=st.session_state.caption_dreams.get("transcription_engine", "auto"),
                    font_size=st.session_state.caption_dreams.get("font_size", 50),
                    extra_params=custom_style,
                    progress_cb=_progress_cb,
                )
                st.session_state.caption_dreams["status"] = "completed"
                st.session_state.caption_dreams["output_path"] = asset.file_path
                mark_step_complete("caption_dreams")
                progress_bar.empty()
                status_text.empty()
                st.success("✅ Captions generated successfully!")
                logger.info(f"Captions done: {asset.file_path}")
                st.rerun()
            except Exception as e:
                st.session_state.caption_dreams["status"] = "error"
                st.session_state.caption_dreams["error"] = str(e)
                logger.error(f"Caption generation error: {e}")
                st.error(f"❌ Error: {e}")
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())

    with preview_col:
        st.markdown("### 🔍 Source Video Preview")
        st.video(st.session_state.caption_dreams["source_video"])

# ── Output section ─────────────────────────────────────────────────────────
if st.session_state.caption_dreams.get("status") == "completed":
    out = st.session_state.caption_dreams.get("output_path")
    if out and Path(out).exists():
        st.markdown("## ✅ Captioned Video")
        st.video(out)
        with open(out, "rb") as f:
            st.download_button("📥 Download Captioned Video", data=f, file_name=Path(out).name, mime="video/mp4")
    else:
        st.warning("Output file not found at expected path.")

render_step_navigation(current_step=7, prev_step_path="pages/6_Video_Assembly.py", next_step_path="pages/8_Social_Media_Upload.py")
