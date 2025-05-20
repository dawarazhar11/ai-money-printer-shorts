import streamlit as st
import os
import json
from pathlib import Path
import sys

# Add the app directory to Python path for relative imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from components.navigation import render_workflow_navigation

# Set page configuration
st.set_page_config(
    page_title="Video Settings | AI Money Printer",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    css_file = Path("assets/css/style.css")
    if css_file.exists():
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Apply custom CSS to fix sidebar text color
st.markdown("""
<style>
    /* Target sidebar with higher specificity */
    [data-testid="stSidebar"] {
        background-color: white !important;
    }
    
    /* Ensure all text inside sidebar is black */
    [data-testid="stSidebar"] * {
        color: black !important;
    }
    
    /* Make sidebar buttons light blue */
    [data-testid="stSidebar"] button {
        background-color: #e6f2ff !important; /* Light blue background */
        color: #0066cc !important; /* Darker blue text */
        border-radius: 6px !important;
    }
    
    /* Hover effect for sidebar buttons */
    [data-testid="stSidebar"] button:hover {
        background-color: #cce6ff !important; /* Slightly darker blue on hover */
    }
    
    /* Target specific sidebar elements with higher specificity */
    .st-emotion-cache-16txtl3, 
    .st-emotion-cache-16idsys, 
    .st-emotion-cache-7ym5gk,
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] span {
        color: black !important;
    }
    
    /* Target sidebar navigation specifically */
    section[data-testid="stSidebar"] > div > div > div > div > div > ul,
    section[data-testid="stSidebar"] > div > div > div > div > div > ul * {
        color: black !important;
    }
    
    /* Ensure sidebar background stays white even after loading */
    section[data-testid="stSidebar"] > div {
        background-color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Render navigation sidebar
render_workflow_navigation()

def save_settings(settings_dict):
    """Save settings to a JSON file"""
    # Create config directory if it doesn't exist
    config_dir = Path("config/user_data")
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # Save settings to JSON file
    with open(config_dir / "project_settings.json", "w") as f:
        json.dump(settings_dict, f, indent=4)
    
    return True

def load_settings():
    """Load settings from JSON file if it exists"""
    config_file = Path("config/user_data/project_settings.json")
    if config_file.exists():
        with open(config_file, "r") as f:
            return json.load(f)
    return {
        "video_duration": 30,
        "broll_segments": 3,
        "project_name": "My Short Video"
    }

# Load existing settings if available
settings = load_settings()

# Header and description
st.title("⚙️ Video Settings")
st.markdown("""
Configure the basic parameters for your short-form video. These settings will be used throughout the production process.
""")

# Form for settings
with st.form("settings_form"):
    # Project name
    project_name = st.text_input(
        "Project Name",
        value=settings.get("project_name", "My Short Video"),
        help="Give your project a descriptive name"
    )
    
    # Video duration in seconds
    video_duration = st.number_input(
        "Total Video Duration (seconds)",
        min_value=10,
        max_value=180,
        value=settings.get("video_duration", 30),
        step=5,
        help="How long should the final video be (in seconds)"
    )
    
    # Number of B-Roll segments
    broll_segments = st.number_input(
        "Number of B-Roll Segments",
        min_value=1,
        max_value=10,
        value=settings.get("broll_segments", 3),
        step=1,
        help="How many B-Roll segments to include in the video"
    )
    
    # Show advanced settings expand/collapse
    with st.expander("Advanced Settings"):
        resolution = st.selectbox(
            "Video Resolution",
            options=["480x736 (9:16)", "1080x1920 (9:16)", "1920x1080 (16:9)", "1080x1080 (1:1)"],
            index=1,
            help="Choose the aspect ratio for your short"
        )
        
        max_broll_duration = st.slider(
            "Maximum B-Roll Duration (seconds)",
            min_value=2,
            max_value=15,
            value=settings.get("max_broll_duration", 5),
            step=1,
            help="Maximum duration for any single B-Roll segment"
        )
    
    # Submit button
    submit = st.form_submit_button("Save Settings")
    
    if submit:
        # Create settings dictionary
        updated_settings = {
            "project_name": project_name,
            "video_duration": video_duration,
            "broll_segments": broll_segments,
            "resolution": resolution.split(" ")[0],
            "max_broll_duration": max_broll_duration
        }
        
        # Save settings
        if save_settings(updated_settings):
            st.session_state["settings"] = updated_settings
            # Mark settings step as complete
            from utils.session_state import mark_step_complete
            mark_step_complete("step_0")
            st.success("Settings saved successfully! You can now proceed to the next step.")

# Display next button if settings have been saved
if "settings" in st.session_state or os.path.exists("config/user_data/project_settings.json"):
    st.markdown("---")
    
    # Display a summary of current settings
    st.subheader("Current Settings")
    current_settings = st.session_state.get("settings", load_settings())
    
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"**Project Name:** {current_settings['project_name']}")
        st.info(f"**Video Duration:** {current_settings['video_duration']} seconds")
    
    with col2:
        st.info(f"**B-Roll Segments:** {current_settings['broll_segments']}")
        if "resolution" in current_settings:
            st.info(f"**Resolution:** {current_settings['resolution']}")
    
    # Next button
    if st.button("Next: Blueprint Setup →", type="primary"):
        st.switch_page("pages/2_Blueprint.py") 