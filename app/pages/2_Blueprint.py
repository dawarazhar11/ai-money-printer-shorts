import streamlit as st
import os
import sys
from pathlib import Path

# Add the app directory to Python path for relative imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from components.navigation import render_workflow_navigation, render_step_navigation
from utils.session_state import get_settings

# Set page configuration
st.set_page_config(
    page_title="Video Blueprint | AI Money Printer",
    page_icon="📝",
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

# Load settings
settings = get_settings()

# Page header
st.title("📝 Video Blueprint Setup")
st.markdown("""
Based on your settings, let's set up the blueprint for your short video.
""")

# Display the project settings
st.subheader("Project Settings")
col1, col2 = st.columns(2)
with col1:
    st.info(f"**Project Name:** {settings['project_name']}")
    st.info(f"**Video Duration:** {settings['video_duration']} seconds")

with col2:
    st.info(f"**B-Roll Segments:** {settings['broll_segments']}")
    if "resolution" in settings:
        st.info(f"**Resolution:** {settings['resolution']}")

st.markdown("---")

# Placeholder for blueprint setup functionality
st.subheader("Blueprint Timeline")
st.info("This is a placeholder for the Blueprint Setup step. In the next implementation, you'll be able to visualize your video timeline here.")

st.markdown("Your video will be segmented based on the settings you've provided. The next step will allow you to input your script and segment it into A-Roll and B-Roll sections.")

# Navigation buttons
st.markdown("---")
render_step_navigation(
    current_step=1,
    prev_step_path="pages/1_Settings.py",
    next_step_path="pages/3_Script_Segmentation.py"
) 