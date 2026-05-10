import streamlit as st
import os
from pathlib import Path

# Set page configuration
st.set_page_config(
    page_title="ReelForge - AI Video Shorts Generator",
    page_icon="🎬",
    layout="centered",
    initial_sidebar_state="expanded"
)

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

# Load custom CSS
def load_css():
    css_file = Path("assets/css/style.css")
    if css_file.exists():
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Create user_data directory if it doesn't exist
Path("config/user_data").mkdir(parents=True, exist_ok=True)

# App header
st.title("🎬 ReelForge")
st.subheader("AI-powered short-form video production pipeline")

# App description
st.markdown("""
### Turn your ideas into engaging short-form videos

This app guides you through creating professional short-form videos by automating the most time-consuming parts of the process.

**Complete the following steps to create your video:**

1. **⚙️ Settings** - Configure your project settings
2. **📝 Video Blueprint Setup** - Visualize video structure and segments
3. **✂️ Script Segmentation** - Organize your script into A-Roll and B-Roll sections
4. **🔍 B-Roll Prompt Generation** - Create optimized prompts for AI-generated visuals
5. **⚡ Parallel Content Production** - Generate both A-Roll and B-Roll simultaneously
6. **🎬 Seamless Video Assembly** - Stitch all segments together with perfect timing
7. **💬 Captioning Enhancement** - Add stylized captions synced with your voice
8. **🚀 Multi-Platform Publishing** - Export for YouTube, TikTok, and Instagram
""")

# Get started button
st.markdown("---")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    if st.button("Get Started 🚀", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Settings.py")

# Footer
st.markdown("---")
st.caption("ReelForge | v1.0.0")
