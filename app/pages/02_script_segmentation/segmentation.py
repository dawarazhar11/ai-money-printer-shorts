import streamlit as st
import os
import sys
import json
from pathlib import Path
import re

# Add the app directory to Python path for relative imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from components.navigation import render_workflow_navigation, render_step_navigation
from components.progress import render_step_header
from utils.session_state import get_settings, get_project_path, mark_step_complete

# Set page configuration
st.set_page_config(
    page_title="Script Segmentation | AI Money Printer",
    page_icon="✂️",
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

# Render navigation sidebar
render_workflow_navigation()

# Load settings
settings = get_settings()
project_path = get_project_path()

# Initialize session state variables
if "script" not in st.session_state:
    st.session_state.script = ""
if "segments" not in st.session_state:
    st.session_state.segments = []
if "auto_segmented" not in st.session_state:
    st.session_state.auto_segmented = False

# Function to load saved script if exists
def load_saved_script():
    script_file = project_path / "script.json"
    if script_file.exists():
        with open(script_file, "r") as f:
            data = json.load(f)
            st.session_state.script = data.get("full_script", "")
            st.session_state.segments = data.get("segments", [])
            return True
    return False

# Function to save script and segments
def save_script_segments(script, segments):
    script_file = project_path / "script.json"
    data = {
        "full_script": script,
        "segments": segments
    }
    with open(script_file, "w") as f:
        json.dump(data, f, indent=4)
    return True

# Page header
render_step_header(2, "Script Segmentation", 8)
st.title("✂️ Script Segmentation")
st.markdown("""
Break down your script into alternating A-Roll and B-Roll segments. 
- **A-Roll**: Your on-camera talking segments
- **B-Roll**: Complementary visuals with voiceover

The script will follow a sequential pattern with A-Roll and B-Roll segments alternating.
The first and last segments will always be A-Roll.
""")

# Check if script was previously saved
has_saved_script = load_saved_script()

# Script input section
st.subheader("Enter Your Script")
script_text = st.text_area(
    "Paste your full script below",
    value=st.session_state.script,
    height=200,
    help="Enter the complete script for your video",
    placeholder="Enter your complete script here. It will be segmented into A-Roll and B-Roll sections."
)

# Auto-segmentation section
st.subheader("Script Segmentation")

# Auto-segment script based on number of B-Roll segments
def auto_segment_script(script_text, num_b_roll_segments):
    if not script_text:
        return []
    
    # Split script into sentences
    sentences = re.split(r'(?<=[.!?])\s+', script_text.strip())
    sentences = [s for s in sentences if s.strip()]
    
    if len(sentences) < 2:
        return [{"type": "A-Roll", "content": script_text}]
    
    # Calculate segments
    # Want to have format: A-B-A-B-A... ending with A
    # Total segments = (num_b_roll_segments * 2) + 1
    total_segments = (num_b_roll_segments * 2) + 1
    
    # Distribute sentences among segments
    segments = []
    sentences_per_segment = max(1, len(sentences) // total_segments)
    
    # Create segments
    for i in range(total_segments):
        start_idx = i * sentences_per_segment
        end_idx = start_idx + sentences_per_segment if i < total_segments - 1 else len(sentences)
        segment_content = " ".join(sentences[start_idx:end_idx]).strip()
        
        if i % 2 == 0:
            # A-Roll segments (0, 2, 4, etc.)
            segments.append({"type": "A-Roll", "content": segment_content})
        else:
            # B-Roll segments (1, 3, 5, etc.)
            segments.append({"type": "B-Roll", "content": segment_content})
    
    return segments

if st.button("Auto-Segment Script"):
    if script_text:
        st.session_state.segments = auto_segment_script(script_text, settings["broll_segments"])
        st.session_state.script = script_text
        st.session_state.auto_segmented = True
        st.success(f"Script automatically segmented into {len(st.session_state.segments)} segments")
    else:
        st.warning("Please enter a script before segmenting")

# Display and edit segments
if st.session_state.segments:
    st.markdown("### Review and Edit Segments")
    st.info("You can adjust the segments below. Make sure the content flows naturally between segments.")
    
    updated_segments = []
    
    for i, segment in enumerate(st.session_state.segments):
        with st.expander(f"{segment['type']} - Segment {i+1}", expanded=True):
            segment_type = st.selectbox(
                "Segment Type",
                options=["A-Roll", "B-Roll"],
                index=0 if segment["type"] == "A-Roll" else 1,
                key=f"type_{i}"
            )
            
            segment_content = st.text_area(
                "Content",
                value=segment["content"],
                height=100,
                key=f"content_{i}"
            )
            
            updated_segments.append({
                "type": segment_type,
                "content": segment_content
            })
    
    # Update session state with edited segments
    st.session_state.segments = updated_segments
    
    # Display segment timeline visualization
    st.subheader("Segment Timeline")
    
    timeline_cols = st.columns(len(st.session_state.segments))
    
    for i, (segment, col) in enumerate(zip(st.session_state.segments, timeline_cols)):
        if segment["type"] == "A-Roll":
            col.markdown(f"""
            <div style="background-color:#06d6a0; color:white; padding:10px; border-radius:5px; text-align:center; height:80px;">
            <strong>A-Roll {i+1}</strong>
            </div>
            """, unsafe_allow_html=True)
        else:
            col.markdown(f"""
            <div style="background-color:#118ab2; color:white; padding:10px; border-radius:5px; text-align:center; height:80px;">
            <strong>B-Roll {i+1}</strong>
            </div>
            """, unsafe_allow_html=True)
    
    # Save script and segments
    if st.button("Save Segmentation", type="primary"):
        if save_script_segments(script_text, st.session_state.segments):
            mark_step_complete("step_2")
            st.success("Script and segments saved successfully!")
else:
    if has_saved_script:
        st.info("Loaded previously saved script. You can make changes and save again.")
    else:
        st.info("Enter your script and click 'Auto-Segment Script' to break it down into A-Roll and B-Roll segments.")

# Navigation buttons
st.markdown("---")
render_step_navigation(
    current_step=2,
    prev_step_path="pages/01_blueprint_setup/blueprint.py",
    next_step_path="pages/03_broll_prompt_generation/prompt_generator.py"
)
