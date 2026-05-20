"""Settings page — project + system configuration.

Two layers:
  • Project settings   → JSON at config/user_data/project_settings.json
                         (downstream pages read this via utils.session_state)
  • System settings    → YAML at config.yaml via app.core.config.config_manager
                         (LLM, TTS, HeyGen, Replicate, ComfyUI, Publishing)
"""

import json
import os
import sys
from pathlib import Path

import streamlit as st

# Make app/ importable for sibling modules
sys.path.append(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from components.navigation import render_workflow_navigation  # noqa: E402
from core.catalogs.llm_presets import (  # noqa: E402
    LLM_PRESETS,
    find_preset_by_base_url_and_model,
    get_preset,
    get_preset_names,
)
from core.catalogs.tts_voices import EDGE_TTS_VOICES  # noqa: E402
from core.config import config_manager  # noqa: E402
from utils.session_state import mark_step_complete  # noqa: E402


# ─── Page setup ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Settings | ReelForge",
    page_icon="⚙️",
    layout="centered",
    initial_sidebar_state="expanded",
)


def _load_css() -> None:
    css = Path("assets/css/style.css")
    if css.exists():
        st.markdown(f"<style>{css.read_text()}</style>", unsafe_allow_html=True)


_load_css()
render_workflow_navigation()


# ─── Project settings (legacy contract — DO NOT BREAK) ─────────────────────

PROJECT_SETTINGS_PATH = Path("config/user_data/project_settings.json")
RESOLUTIONS = ["480x736 (9:16)", "1080x1920 (9:16)", "1920x1080 (16:9)", "1080x1080 (1:1)"]
DEFAULT_PROJECT_SETTINGS = {
    "project_name": "My Short Video",
    "video_duration": 30,
    "broll_segments": 3,
    "resolution": "1080x1920",
    "max_broll_duration": 5,
}


def _load_project_settings() -> dict:
    if PROJECT_SETTINGS_PATH.exists():
        try:
            return json.loads(PROJECT_SETTINGS_PATH.read_text())
        except json.JSONDecodeError:
            pass
    return dict(DEFAULT_PROJECT_SETTINGS)


def _save_project_settings(payload: dict) -> None:
    PROJECT_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROJECT_SETTINGS_PATH.write_text(json.dumps(payload, indent=4))


# ─── Helpers ────────────────────────────────────────────────────────────────


def _voice_locales() -> list[str]:
    seen: list[str] = []
    for v in EDGE_TTS_VOICES:
        if v["locale"] not in seen:
            seen.append(v["locale"])
    return seen


def _commit_system_update(updates: dict, label: str) -> None:
    try:
        config_manager.update(updates)
        config_manager.save()
        st.success(f"{label} saved to config.yaml")
    except Exception as exc:
        st.error(f"Failed to save {label}: {exc}")


# ─── Header ─────────────────────────────────────────────────────────────────

st.title("⚙️ Settings")
st.caption("Project basics live in `project_settings.json`. API keys and backend choices live in `config.yaml`.")


# ─── 1. Project settings ────────────────────────────────────────────────────

st.subheader("1. Project")

project = _load_project_settings()

with st.form("project_form"):
    project_name = st.text_input(
        "Project name",
        value=project.get("project_name", "My Short Video"),
        help="Used as the project directory name under config/user_data/.",
    )
    video_duration = st.number_input(
        "Total video duration (seconds)",
        min_value=10,
        max_value=180,
        value=int(project.get("video_duration", 30)),
        step=5,
    )
    broll_segments = st.number_input(
        "Number of B-Roll segments",
        min_value=1,
        max_value=10,
        value=int(project.get("broll_segments", 3)),
        step=1,
    )

    with st.expander("Advanced"):
        # Find the index for current resolution; default to 1080x1920 if no match
        current_res = project.get("resolution", "1080x1920")
        res_index = next(
            (i for i, r in enumerate(RESOLUTIONS) if r.startswith(current_res)),
            1,
        )
        resolution = st.selectbox("Resolution", options=RESOLUTIONS, index=res_index)
        max_broll_duration = st.slider(
            "Maximum B-Roll segment duration (seconds)",
            min_value=2,
            max_value=15,
            value=int(project.get("max_broll_duration", 5)),
            step=1,
        )

    if st.form_submit_button("Save project settings"):
        payload = {
            "project_name": project_name,
            "video_duration": video_duration,
            "broll_segments": broll_segments,
            "resolution": resolution.split(" ")[0],
            "max_broll_duration": max_broll_duration,
        }
        _save_project_settings(payload)
        st.session_state["settings"] = payload
        mark_step_complete("step_0")
        st.success("Project settings saved.")


# ─── 2. LLM ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("2. LLM")

llm_cfg = config_manager.llm()
preset_names = ["Custom"] + get_preset_names()
current_preset = (
    find_preset_by_base_url_and_model(llm_cfg.base_url, llm_cfg.model) or "Custom"
)

with st.expander("Configure LLM", expanded=not config_manager.config.is_llm_configured()):
    preset_choice = st.selectbox(
        "Provider preset",
        options=preset_names,
        index=preset_names.index(current_preset),
        help="Picks sensible base_url / model defaults. All providers route through the OpenAI SDK.",
    )

    if preset_choice != "Custom":
        preset = get_preset(preset_choice)
        st.caption(f"API key page: {preset.get('api_key_url', 'n/a')}")
        default_base_url = preset["base_url"]
        default_model = preset["model"]
        default_api_key = preset.get("default_api_key", llm_cfg.api_key)
    else:
        default_base_url = llm_cfg.base_url
        default_model = llm_cfg.model
        default_api_key = llm_cfg.api_key

    with st.form("llm_form"):
        api_key = st.text_input("API key", value=default_api_key, type="password")
        base_url = st.text_input("Base URL", value=default_base_url)
        model = st.text_input("Model", value=default_model)
        if st.form_submit_button("Save LLM settings"):
            _commit_system_update(
                {"llm": {"api_key": api_key, "base_url": base_url, "model": model}},
                "LLM settings",
            )

# Ollama (kept separate — different shape, always-local)
with st.expander("Ollama (local LLM, free)"):
    ollama_cfg = config_manager.ollama()
    with st.form("ollama_form"):
        ollama_url = st.text_input("API URL", value=ollama_cfg.api_url)
        ollama_model = st.text_input("Model", value=ollama_cfg.model)
        if st.form_submit_button("Save Ollama settings"):
            _commit_system_update(
                {"ollama": {"api_url": ollama_url, "model": ollama_model}},
                "Ollama settings",
            )


# ─── 3. TTS ─────────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("3. TTS (A-Roll voice)")

tts_cfg = config_manager.config.tts

with st.expander("Configure TTS", expanded=True):
    with st.form("tts_form"):
        mode = st.selectbox(
            "Inference mode",
            options=["local", "comfyui", "heygen"],
            index=["local", "comfyui", "heygen"].index(tts_cfg.inference_mode),
            help="local=Edge-TTS (free), comfyui=workflow-driven, heygen=avatar voice",
        )

        locales = _voice_locales()
        current_locale = next(
            (v["locale"] for v in EDGE_TTS_VOICES if v["id"] == tts_cfg.local.voice),
            "en-US",
        )
        locale = st.selectbox(
            "Voice locale",
            options=locales,
            index=locales.index(current_locale) if current_locale in locales else 0,
        )

        voices_for_locale = [v for v in EDGE_TTS_VOICES if v["locale"] == locale]
        voice_labels = [v["label"] for v in voices_for_locale]
        voice_ids = [v["id"] for v in voices_for_locale]
        voice_index = voice_ids.index(tts_cfg.local.voice) if tts_cfg.local.voice in voice_ids else 0
        voice_label = st.selectbox("Voice", options=voice_labels, index=voice_index)
        voice_id = voice_ids[voice_labels.index(voice_label)]

        speed = st.slider(
            "Speed", min_value=0.5, max_value=2.0, value=float(tts_cfg.local.speed), step=0.05
        )

        if st.form_submit_button("Save TTS settings"):
            _commit_system_update(
                {"tts": {"inference_mode": mode, "local": {"voice": voice_id, "speed": speed}}},
                "TTS settings",
            )


# ─── 4. HeyGen ──────────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("4. HeyGen (avatar A-Roll)")

heygen_cfg = config_manager.heygen()

with st.expander("Configure HeyGen", expanded=not config_manager.config.is_heygen_configured()):
    with st.form("heygen_form"):
        hg_key = st.text_input("API key", value=heygen_cfg.api_key, type="password")
        hg_avatar = st.text_input("Default avatar ID", value=heygen_cfg.default_avatar_id)
        hg_voice = st.text_input("Default voice ID", value=heygen_cfg.default_voice_id)
        hg_bg = st.text_input("Chroma background color", value=heygen_cfg.background_color)
        if st.form_submit_button("Save HeyGen settings"):
            _commit_system_update(
                {
                    "heygen": {
                        "api_key": hg_key,
                        "default_avatar_id": hg_avatar,
                        "default_voice_id": hg_voice,
                        "background_color": hg_bg,
                    }
                },
                "HeyGen settings",
            )


# ─── 5. Replicate ───────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("5. Replicate (cloud B-Roll)")

rep_cfg = config_manager.replicate()

with st.expander("Configure Replicate"):
    with st.form("replicate_form"):
        rep_token = st.text_input("API token", value=rep_cfg.api_token, type="password")
        rep_img = st.text_input("Default image model", value=rep_cfg.default_image_model)
        rep_vid = st.text_input("Default video model", value=rep_cfg.default_video_model)
        if st.form_submit_button("Save Replicate settings"):
            _commit_system_update(
                {
                    "replicate": {
                        "api_token": rep_token,
                        "default_image_model": rep_img,
                        "default_video_model": rep_vid,
                    }
                },
                "Replicate settings",
            )


# ─── 6. ComfyUI / RunningHub ────────────────────────────────────────────────

st.markdown("---")
st.subheader("6. ComfyUI / RunningHub")

cf_cfg = config_manager.comfyui()

with st.expander("Configure ComfyUI"):
    with st.form("comfyui_form"):
        col1, col2 = st.columns(2)
        with col1:
            image_url = st.text_input("Image API URL", value=cf_cfg.image_api_url)
            ws_host = st.text_input("WebSocket host", value=cf_cfg.ws_host)
        with col2:
            video_url = st.text_input("Video API URL", value=cf_cfg.video_api_url)
            ws_port = st.number_input(
                "WebSocket port", min_value=1, max_value=65535, value=int(cf_cfg.ws_port)
            )

        st.divider()
        st.caption("RunningHub (managed cloud)")
        rh_key = st.text_input("RunningHub API key", value=cf_cfg.runninghub_api_key or "", type="password")
        rh_limit = st.number_input(
            "RunningHub concurrent limit",
            min_value=1,
            max_value=10,
            value=int(cf_cfg.runninghub_concurrent_limit),
        )
        rh_instance = st.selectbox(
            "RunningHub instance type",
            options=["default", "plus"],
            index=1 if cf_cfg.runninghub_instance_type == "plus" else 0,
            help="'plus' = 48GB VRAM",
        )

        if st.form_submit_button("Save ComfyUI settings"):
            _commit_system_update(
                {
                    "comfyui": {
                        "image_api_url": image_url,
                        "video_api_url": video_url,
                        "ws_host": ws_host,
                        "ws_port": int(ws_port),
                        "runninghub_api_key": rh_key or None,
                        "runninghub_concurrent_limit": int(rh_limit),
                        "runninghub_instance_type": "plus" if rh_instance == "plus" else None,
                    }
                },
                "ComfyUI settings",
            )


# ─── 7. Publishing ──────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("7. Publishing")

pub_cfg = config_manager.publishing()

with st.expander("YouTube"):
    with st.form("youtube_form"):
        yt_secret = st.text_input("Client secret JSON path", value=pub_cfg.youtube.client_secret_path)
        yt_token = st.text_input("Token cache path", value=pub_cfg.youtube.token_cache_path)
        yt_privacy = st.selectbox(
            "Default privacy",
            options=["private", "unlisted", "public"],
            index=["private", "unlisted", "public"].index(pub_cfg.youtube.default_privacy),
        )
        if st.form_submit_button("Save YouTube settings"):
            _commit_system_update(
                {
                    "publishing": {
                        "youtube": {
                            "client_secret_path": yt_secret,
                            "token_cache_path": yt_token,
                            "default_privacy": yt_privacy,
                        }
                    }
                },
                "YouTube settings",
            )

with st.expander("TikTok"):
    with st.form("tiktok_form"):
        tt_key = st.text_input("Client key", value=pub_cfg.tiktok.client_key)
        tt_secret = st.text_input("Client secret", value=pub_cfg.tiktok.client_secret, type="password")
        tt_redirect = st.text_input("Redirect URI", value=pub_cfg.tiktok.redirect_uri)
        if st.form_submit_button("Save TikTok settings"):
            _commit_system_update(
                {
                    "publishing": {
                        "tiktok": {
                            "client_key": tt_key,
                            "client_secret": tt_secret,
                            "redirect_uri": tt_redirect,
                        }
                    }
                },
                "TikTok settings",
            )

with st.expander("Instagram"):
    with st.form("instagram_form"):
        ig_token = st.text_input("Access token", value=pub_cfg.instagram.access_token, type="password")
        ig_account = st.text_input("Business account ID", value=pub_cfg.instagram.business_account_id)
        if st.form_submit_button("Save Instagram settings"):
            _commit_system_update(
                {
                    "publishing": {
                        "instagram": {
                            "access_token": ig_token,
                            "business_account_id": ig_account,
                        }
                    }
                },
                "Instagram settings",
            )


# ─── 8. Status panel ────────────────────────────────────────────────────────

st.markdown("---")
st.subheader("📊 Configuration status")

cfg = config_manager.config


def _badge(label: str, ok: bool, note: str = "") -> None:
    icon = "✅" if ok else "❌"
    color = "green" if ok else "red"
    suffix = f" — {note}" if note else ""
    st.markdown(f":{color}[{icon} **{label}**{suffix}]")


col_a, col_b = st.columns(2)
with col_a:
    _badge("LLM", cfg.is_llm_configured(), cfg.llm.model or "no model")
    _badge("Ollama (local)", cfg.is_ollama_configured(), cfg.ollama.model)
    _badge("HeyGen avatar", cfg.is_heygen_configured(), "A-Roll talking head")
    _badge("Replicate cloud", cfg.is_replicate_configured(), "B-Roll fallback")

with col_b:
    _badge("A-Roll backend", cfg.has_a_roll_backend(), "HeyGen or local TTS")
    _badge("B-Roll backend", cfg.has_image_backend(), "ComfyUI or Replicate")

ok, missing = cfg.validate_required()
if ok:
    st.success("✅ Configuration is complete — ready to generate.")
else:
    st.warning("Missing required backends:\n\n" + "\n".join(f"- {m}" for m in missing))


# ─── Reload / next ──────────────────────────────────────────────────────────

st.markdown("---")
col_left, col_right = st.columns([1, 2])
with col_left:
    if st.button("🔄 Reload from disk"):
        config_manager.reload()
        st.success("Reloaded.")
        st.rerun()

with col_right:
    if "settings" in st.session_state or PROJECT_SETTINGS_PATH.exists():
        if st.button("Next: Blueprint Setup →", type="primary"):
            st.switch_page("pages/2_Blueprint.py")
