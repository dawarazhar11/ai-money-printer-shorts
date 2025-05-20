import streamlit as st
import os
import sys
from pathlib import Path
import numpy as np
import time
from datetime import datetime
import cv2
import traceback

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path")
    print("Successfully imported local modules")

# Now import our helper modules
try:
    from utils.video.assembly import (
        assemble_video as helper_assemble_video,
        check_file,
        MOVIEPY_AVAILABLE
    )
    from utils.video.simple_assembly import simple_assemble_video
except ImportError as e:
    print(f"Error importing video assembly module: {str(e)}")
    # Alternative import paths in case the first one fails
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from utils.video.assembly import (
            assemble_video as helper_assemble_video,
            check_file,
            MOVIEPY_AVAILABLE
        )
        from utils.video.simple_assembly import simple_assemble_video
        print("Successfully imported video assembly module using alternative path")
    except ImportError as e2:
        print(f"Alternative import also failed: {str(e2)}")
        # Create fallback values if import fails
        helper_assemble_video = None
        check_file = None
        MOVIEPY_AVAILABLE = False
        simple_assemble_video = None

# Try to import MoviePy, show helpful error if not available
try:
    import moviepy.editor as mp
    from moviepy.video.fx import resize, speedx
    MOVIEPY_AVAILABLE = True
except ImportError:
    st.error("MoviePy is not available. Installing required packages...")
    st.info("Please run: `pip install moviepy==1.0.3` in your virtual environment")
    MOVIEPY_AVAILABLE = False
    # Create dummy classes/functions to avoid errors
    class DummyMoviePy:
        def __getattr__(self, name):
            return lambda *args, **kwargs: None
    mp = DummyMoviePy()
    resize = lambda *args, **kwargs: None
    speedx = lambda *args, **kwargs: None

# Import other modules
from components.progress import render_step_header
from components.navigation import render_workflow_navigation, render_step_navigation
from utils.session_state import get_settings, get_project_path, mark_step_complete

# Rest of the imports
import json
from pathlib import Path
import subprocess

# Set page configuration
st.set_page_config(
    page_title="Video Assembly | AI Money Printer",
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

# Render navigation sidebar
render_workflow_navigation()

# Load settings and project path
settings = get_settings()
project_path = get_project_path()

# Initialize session state variables
if "video_assembly" not in st.session_state:
    st.session_state.video_assembly = {
        "status": "not_started",
        "progress": 0,
        "output_path": None,
        "error": None,
        "sequence": []
    }

# Function to load content status from previous step
def load_content_status():
    status_file = project_path / "content_status.json"
    if status_file.exists():
        try:
            with open(status_file, "r") as f:
                status_data = json.load(f)
                # Validate structure
                if "aroll" in status_data and "broll" in status_data:
                    return status_data
                else:
                    st.error("Content status file has invalid structure.")
                    return None
        except Exception as e:
            st.error(f"Error loading content status: {str(e)}")
            return None
    else:
        st.error("Content status file not found. Please complete the Content Production step first.")
        return None

# Function to load segments
def load_segments():
    script_file = project_path / "script.json"
    if script_file.exists():
        try:
            with open(script_file, "r") as f:
                data = json.load(f)
                segments = data.get("segments", [])
                return segments
        except Exception as e:
            st.error(f"Error loading segments: {str(e)}")
            return []
    else:
        st.error("Script segments file not found. Please complete the Script Segmentation step first.")
        return []

# Function to resize video to target resolution (9:16 aspect ratio)
def resize_video(clip, target_resolution=(1080, 1920)):
    """Resize video clip to target resolution maintaining aspect ratio with padding if needed"""
    # Get original dimensions
    w, h = clip.size
    
    # Calculate target aspect ratio
    target_aspect = target_resolution[0] / target_resolution[1]  # width/height
    current_aspect = w / h
    
    if current_aspect > target_aspect:
        # Video is wider than target aspect ratio - fit to width
        new_width = target_resolution[0]
        new_height = int(new_width / current_aspect)
        resized_clip = clip.resize(width=new_width, height=new_height)
        
        # Add padding to top and bottom
        padding_top = (target_resolution[1] - new_height) // 2
        padding_bottom = target_resolution[1] - new_height - padding_top
        
        # Create black background
        bg = mp.ColorClip(size=target_resolution, color=(0, 0, 0), duration=clip.duration)
        
        # Position resized clip on background
        final_clip = mp.CompositeVideoClip([
            bg,
            resized_clip.set_position(("center", padding_top))
        ])
    else:
        # Video is taller than target aspect ratio - fit to height
        new_height = target_resolution[1]
        new_width = int(new_height * current_aspect)
        resized_clip = clip.resize(height=new_height, width=new_width)
        
        # Add padding to left and right
        padding_left = (target_resolution[0] - new_width) // 2
        
        # Create black background
        bg = mp.ColorClip(size=target_resolution, color=(0, 0, 0), duration=clip.duration)
        
        # Position resized clip on background
        final_clip = mp.CompositeVideoClip([
            bg,
            resized_clip.set_position((padding_left, 0))
        ])
        
    return final_clip.set_duration(clip.duration)

def get_aroll_filepath(segment_id, segment_data):
    """
    Get the filepath for an A-Roll segment, supporting both naming formats
    
    Args:
        segment_id: ID of the segment (e.g., 'segment_0')
        segment_data: Data for the segment
        
    Returns:
        str: Path to the A-Roll file if found, None otherwise
    """
    # Check the file path in the content status
    if "file_path" in segment_data:
        file_path = segment_data["file_path"]
        if os.path.exists(file_path):
            return file_path
    
    # Try alternative formats if the primary file path doesn't exist
    segment_num = segment_id.split('_')[-1]
    prompt_id = segment_data.get('prompt_id', '')
    
    # Different file naming patterns to try
    patterns = [
        # Original expected format (short ID)
        f"media/a-roll/fetched_aroll_segment_{segment_num}_{prompt_id[:8]}.mp4",
        # Full path with short ID
        f"{app_root}/media/a-roll/fetched_aroll_segment_{segment_num}_{prompt_id[:8]}.mp4",
        # HeyGen format
        f"media/a-roll/heygen_{prompt_id}.mp4",
        # Full path with HeyGen format
        f"{app_root}/media/a-roll/heygen_{prompt_id}.mp4"
    ]
    
    # Try each pattern
    for pattern in patterns:
        if os.path.exists(pattern):
            print(f"Found A-Roll file: {pattern}")
            return pattern
            
    print(f"A-Roll file not found for {segment_id} with prompt_id {prompt_id}")
    return None

# Function to create assembly sequence
def create_assembly_sequence():
    """
    Create a sequence of video segments for assembly based on the content status
    and selected sequence pattern
    
    Returns:
        dict: Result containing status and sequence
    """
    # Get content status
    content_status = load_content_status()
    if not content_status:
        return {"status": "error", "message": "Could not load content status"}
        
    aroll_segments = content_status.get("aroll", {})
    broll_segments = content_status.get("broll", {})
    
    print(f"Found {len(aroll_segments)} A-Roll segments and {len(broll_segments)} B-Roll segments")
    print(f"A-Roll keys: {list(aroll_segments.keys())}")
    print(f"B-Roll keys: {list(broll_segments.keys())}")
    
    # Get selected sequence pattern
    selected_sequence = st.session_state.get("selected_sequence", "Standard (A-Roll start, B-Roll middle with A-Roll audio, A-Roll end)")
    
    # Create a sequence for assembly based on the selected pattern
    assembly_sequence = []
    
    # Check how many segments we have
    total_aroll_segments = len(aroll_segments)
    total_broll_segments = len(broll_segments)
    
    if total_aroll_segments == 0:
        return {"status": "error", "message": "No A-Roll segments found"}
    
    # Standard pattern (original implementation)
    if "Standard" in selected_sequence:
        # First segment is A-Roll only
        if "segment_0" in aroll_segments:
            aroll_data = aroll_segments["segment_0"]
            aroll_path = get_aroll_filepath("segment_0", aroll_data)
            
            if aroll_path:
                print(f"Adding A-Roll segment 0 with path: {aroll_path}")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": "segment_0"
                })
            else:
                st.error(f"A-Roll file not found: {aroll_data.get('file_path', 'No path specified')}")
        
        # Middle segments: B-Roll visuals with A-Roll audio
        for i in range(1, total_aroll_segments - 1):
            aroll_segment_id = f"segment_{i}"
            broll_segment_id = f"segment_{i-1}"  # B-Roll segments are named "segment_X" in content_status.json
            
            if aroll_segment_id in aroll_segments and broll_segment_id in broll_segments:
                aroll_data = aroll_segments[aroll_segment_id]
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                broll_path = broll_data.get("file_path")
                
                if aroll_path and broll_path and os.path.exists(broll_path):
                    print(f"Adding B-Roll segment {i-1} with A-Roll segment {i}")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": aroll_segment_id,
                        "broll_id": broll_segment_id
                    })
                else:
                    if not aroll_path:
                        st.error(f"A-Roll file not found for {aroll_segment_id}")
                    if not broll_path or not os.path.exists(broll_path):
                        st.error(f"B-Roll file not found for {broll_segment_id}")
        
        # Last segment is A-Roll only
        last_segment_id = f"segment_{total_aroll_segments - 1}"
        if last_segment_id in aroll_segments:
            aroll_data = aroll_segments[last_segment_id]
            aroll_path = get_aroll_filepath(last_segment_id, aroll_data)
            
            if aroll_path:
                print(f"Adding final A-Roll segment with path: {aroll_path}")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": last_segment_id
                })
            else:
                st.error(f"A-Roll file not found: {aroll_data.get('file_path', 'No path specified')}")
    
    # A-Roll Bookends pattern
    elif "Bookends" in selected_sequence:
        # First segment is A-Roll only
        if "segment_0" in aroll_segments:
            aroll_data = aroll_segments["segment_0"]
            aroll_path = get_aroll_filepath("segment_0", aroll_data)
            
            if aroll_path:
                print(f"Adding A-Roll segment 0 with path: {aroll_path}")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": "segment_0"
                })
            else:
                st.error(f"A-Roll file not found: {aroll_data.get('file_path', 'No path specified')}")
        
        # All middle segments use B-Roll visuals with A-Roll audio
        for i in range(1, total_aroll_segments - 1):
            aroll_segment_id = f"segment_{i}"
            # Use the appropriate B-Roll segment or cycle through available ones
            broll_index = (i - 1) % total_broll_segments
            broll_segment_id = f"segment_{broll_index}"
            
            if aroll_segment_id in aroll_segments and broll_segment_id in broll_segments:
                aroll_data = aroll_segments[aroll_segment_id]
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                broll_path = broll_data.get("file_path")
                
                if aroll_path and broll_path and os.path.exists(broll_path):
                    print(f"Adding B-Roll segment {broll_index} with A-Roll segment {i}")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": aroll_segment_id,
                        "broll_id": broll_segment_id
                    })
            
        # Last segment is A-Roll only
        last_segment_id = f"segment_{total_aroll_segments - 1}"
        if last_segment_id in aroll_segments:
            aroll_data = aroll_segments[last_segment_id]
            aroll_path = get_aroll_filepath(last_segment_id, aroll_data)
            
            if aroll_path:
                print(f"Adding final A-Roll segment with path: {aroll_path}")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": last_segment_id
                })
    
    # A-Roll Sandwich pattern (A-Roll at start, middle, and end)
    elif "Sandwich" in selected_sequence:
        # Calculate which segments will be A-Roll vs B-Roll
        total_segments = total_aroll_segments
        a_roll_positions = [0]  # First position is always A-Roll
        
        # Add middle position if we have at least 3 segments
        if total_segments >= 3:
            middle_pos = total_segments // 2
            a_roll_positions.append(middle_pos)
        
        # Add last position if we have at least 2 segments
        if total_segments >= 2:
            a_roll_positions.append(total_segments - 1)
        
        # Create the sequence
        for i in range(total_segments):
            aroll_segment_id = f"segment_{i}"
            
            # If this is a position for A-Roll
            if i in a_roll_positions:
                if aroll_segment_id in aroll_segments:
                    aroll_data = aroll_segments[aroll_segment_id]
                    aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                    
                    if aroll_path:
                        print(f"Adding A-Roll segment {i} with path: {aroll_path}")
                        assembly_sequence.append({
                            "type": "aroll_full",
                            "aroll_path": aroll_path,
                            "broll_path": None,
                            "segment_id": aroll_segment_id
                        })
            # Otherwise use B-Roll with A-Roll audio
            else:
                # Use the appropriate B-Roll segment or cycle through available ones
                broll_index = (i - 1) % total_broll_segments
                broll_segment_id = f"segment_{broll_index}"
                
                if aroll_segment_id in aroll_segments and broll_segment_id in broll_segments:
                    aroll_data = aroll_segments[aroll_segment_id]
                    broll_data = broll_segments[broll_segment_id]
                    
                    aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                    broll_path = broll_data.get("file_path")
                    
                    if aroll_path and broll_path and os.path.exists(broll_path):
                        print(f"Adding B-Roll segment {broll_index} with A-Roll segment {i}")
                        assembly_sequence.append({
                            "type": "broll_with_aroll_audio",
                            "aroll_path": aroll_path,
                            "broll_path": broll_path,
                            "segment_id": aroll_segment_id,
                            "broll_id": broll_segment_id
                        })
    
    # B-Roll Heavy (only first segment uses A-Roll visual)
    elif "B-Roll Heavy" in selected_sequence:
        # First segment is A-Roll only
        if "segment_0" in aroll_segments:
            aroll_data = aroll_segments["segment_0"]
            aroll_path = get_aroll_filepath("segment_0", aroll_data)
            
            if aroll_path:
                print(f"Adding A-Roll segment 0 with path: {aroll_path}")
                assembly_sequence.append({
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "broll_path": None,
                    "segment_id": "segment_0"
                })
        
        # All remaining segments use B-Roll visuals with A-Roll audio
        for i in range(1, total_aroll_segments):
            aroll_segment_id = f"segment_{i}"
            # Use the appropriate B-Roll segment or cycle through available ones
            broll_index = (i - 1) % total_broll_segments
            broll_segment_id = f"segment_{broll_index}"
            
            if aroll_segment_id in aroll_segments and broll_segment_id in broll_segments:
                aroll_data = aroll_segments[aroll_segment_id]
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                broll_path = broll_data.get("file_path")
                
                if aroll_path and broll_path and os.path.exists(broll_path):
                    print(f"Adding B-Roll segment {broll_index} with A-Roll segment {i}")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": aroll_segment_id,
                        "broll_id": broll_segment_id
                    })
    
    if assembly_sequence:
        return {
            "status": "success",
            "sequence": assembly_sequence
        }
    else:
        return {
            "status": "error",
            "message": "No valid segments found for assembly"
        }

# Replace the assemble_video function to include fallback to simple_assembly
def assemble_video():
    """
    Assemble the final video from A-Roll and B-Roll segments
    """
    if not MOVIEPY_AVAILABLE:
        st.error("MoviePy is not available. Installing required packages...")
        st.info("Please run: `python utils/video/dependencies.py` to install required packages")
        return

    # Get the assembly sequence
    sequence_result = create_assembly_sequence()
    if sequence_result["status"] != "success":
        st.error(sequence_result.get("message", "Failed to create assembly sequence"))
        return
        
    assembly_sequence = sequence_result["sequence"]
    
    # Parse selected resolution
    resolution_options = {"1080x1920 (9:16)": (1080, 1920), 
                         "720x1280 (9:16)": (720, 1280), 
                         "1920x1080 (16:9)": (1920, 1080)}
    selected_resolution = st.session_state.get("selected_resolution", "1080x1920 (9:16)")
    width, height = resolution_options[selected_resolution]
    
    # Set up progress reporting
    progress_text = st.empty()
    progress_bar = st.progress(0)
    
    def update_progress(progress, message):
        # Update the progress bar and text
        progress_bar.progress(min(1.0, progress / 100))
        progress_text.text(f"{message} ({int(progress)}%)")
    
    # Perform the video assembly using our helper
    st.info("Assembling video, please wait...")
    update_progress(0, "Starting video assembly")
    
    # Create output directory if it doesn't exist
    output_dir = project_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Display a checkbox to choose assembly method
    use_simple_assembly = st.session_state.get("use_simple_assembly", False)
    st.checkbox("Use simple assembly (FFmpeg direct)", value=use_simple_assembly, 
                help="Use this if you experience issues with MoviePy", 
                key="use_simple_assembly")
    
    try:
        # Try primary assembly method first unless simple assembly is selected
        if not st.session_state.get("use_simple_assembly", False):
            # Call our helper function
            result = helper_assemble_video(
                sequence=assembly_sequence,
                target_resolution=(width, height),
                output_dir=str(output_dir),
                progress_callback=update_progress
            )
            
            # If primary method failed and simple assembly is available, try it
            if result["status"] == "error" and simple_assemble_video:
                st.warning("Primary assembly method failed. Trying simple assembly fallback...")
                update_progress(0, "Starting simple assembly fallback")
                
                # Try fallback method
                result = simple_assemble_video(
                    sequence=assembly_sequence,
                    output_path=None,  # Use default path
                    target_resolution=(width, height),
                    progress_callback=update_progress
                )
        else:
            # Use simple assembly method directly
            result = simple_assemble_video(
                sequence=assembly_sequence,
                output_path=None,  # Use default path
                target_resolution=(width, height),
                progress_callback=update_progress
            )
        
        # Process result
        if result["status"] == "success":
            st.session_state.video_assembly["status"] = "complete"
            st.session_state.video_assembly["output_path"] = result["output_path"]
            
            # Mark step as complete
            mark_step_complete("video_assembly")
            
            st.success(f"Video assembled successfully!")
            update_progress(100, "Video assembly complete")
            st.rerun()
        else:
            st.session_state.video_assembly["status"] = "error"
            st.session_state.video_assembly["error"] = result["message"]
            
            # Display detailed error information
            st.error(f"Video assembly failed: {result['message']}")
            if "missing_files" in result:
                st.warning("Missing files:")
                for missing in result["missing_files"]:
                    st.warning(f" - {missing}")
            
            # Show traceback in expander if available
            if "traceback" in result:
                with st.expander("Error Details"):
                    st.code(result["traceback"])
                    
    except Exception as e:
        st.session_state.video_assembly["status"] = "error"
        st.session_state.video_assembly["error"] = str(e)
        
        st.error(f"Unexpected error during video assembly: {str(e)}")
        with st.expander("Error Details"):
            st.code(traceback.format_exc())

# Replace the assembly options section with this improved version
st.subheader("Assembly Options")

# Add sequence selection
sequence_options = [
    "Standard (A-Roll start, B-Roll middle with A-Roll audio, A-Roll end)",
    "A-Roll Bookends (A-Roll at start and end only, B-Roll middle)",
    "A-Roll Sandwich (A-Roll at start, middle, and end)",
    "B-Roll Heavy (Only first segment uses A-Roll visual)",
    "Custom (Manual Arrangement)"
]
st.session_state.selected_sequence = st.selectbox(
    "Sequence Pattern:", 
    sequence_options,
    index=sequence_options.index(st.session_state.get("selected_sequence", sequence_options[0])),
    key="sequence_selectbox"
)

# If Custom is selected, enable manual editing
if st.session_state.selected_sequence == "Custom (Manual Arrangement)" and not st.session_state.get("enable_manual_editing", False):
    st.session_state.enable_manual_editing = True
    st.rerun()

# Resolution selection
resolution_options = ["1080x1920 (9:16)", "720x1280 (9:16)", "1920x1080 (16:9)"]
st.session_state.selected_resolution = st.selectbox(
    "Output Resolution:", 
    resolution_options,
    index=resolution_options.index(st.session_state.get("selected_resolution", "1080x1920 (9:16)")),
    key="resolution_selectbox_main"
)

# Add a dependency check option
if st.button("Check Dependencies", type="secondary", help="Check if all required packages are installed", key="check_dependencies_main"):
    with st.spinner("Checking dependencies..."):
        try:
            subprocess.run([sys.executable, "utils/video/dependencies.py"], check=True)
            st.success("All dependencies are installed!")
        except Exception as e:
            st.error(f"Error checking dependencies: {str(e)}")
            st.info("Please run `python utils/video/dependencies.py` manually to install required packages")

# Replace the assembly button with an improved version
if st.button("🎬 Assemble Video", type="primary", use_container_width=True, key="assemble_video_main"):
    assemble_video()

# Display output video if completed
if st.session_state.video_assembly["status"] == "complete" and st.session_state.video_assembly["output_path"]:
    st.subheader("Output Video")
    output_path = st.session_state.video_assembly["output_path"]
    
    if os.path.exists(output_path):
        # Display video
        st.video(output_path)
        
        # Download button
        with open(output_path, "rb") as file:
            st.download_button(
                label="📥 Download Video",
                data=file,
                file_name=os.path.basename(output_path),
                mime="video/mp4"
            )
    else:
        st.error("Video file not found. It may have been moved or deleted.")
else:
    st.error("Content data not found. Please complete previous steps before assembling the video.")

# Video Assembly Page
render_step_header(6, "Video Assembly", 8)
st.title("🎬 Video Assembly")
st.markdown("""
Create your final video by assembling A-Roll and B-Roll segments.
This step will combine all the visual assets into a single, coherent video.
""")

# Check if MoviePy is available
if not MOVIEPY_AVAILABLE:
    st.error("⚠️ MoviePy is not available. Video assembly requires MoviePy.")
    st.info("Please install MoviePy by running: `pip install moviepy==1.0.3`")
    
    with st.expander("Installation Instructions"):
        st.markdown("""
        ### Installing MoviePy
        
        1. **Activate your virtual environment**: 
           ```bash
           source .venv/bin/activate
           ```
        
        2. **Install MoviePy and dependencies**:
           ```bash
           pip install moviepy==1.0.3 ffmpeg-python
           ```
           
        3. **Install FFMPEG (if not already installed)**:
           
           On Mac:
           ```bash
           brew install ffmpeg
           ```
           
           On Ubuntu/Debian:
           ```bash
           sudo apt-get install ffmpeg
           ```
           
           On Windows:
           - Download from [ffmpeg.org](https://ffmpeg.org/download.html)
           - Add to your PATH
        
        4. **Restart the Streamlit app**:
           ```bash
           streamlit run pages/6_Video_Assembly.py
           ```
        """)
    st.stop()

# Load content status and segments
content_status = load_content_status()
segments = load_segments()

if content_status and segments:
    # Display summary of available content
    st.subheader("Content Summary")
    
    # Count A-Roll and B-Roll segments
    aroll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
    broll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll"]
    
    # Count completed segments
    aroll_completed = sum(1 for i in range(len(aroll_segments)) 
                         if f"segment_{i}" in content_status["aroll"] and 
                         content_status["aroll"][f"segment_{i}"].get("status") == "complete")
    
    broll_completed = sum(1 for i in range(len(broll_segments)) 
                         if f"segment_{i}" in content_status["broll"] and 
                         content_status["broll"][f"segment_{i}"].get("status") == "complete")
    
    # Display counts
    col1, col2 = st.columns(2)
    with col1:
        st.info(f"A-Roll Segments: {aroll_completed}/{len(aroll_segments)} completed")
    with col2:
        st.info(f"B-Roll Segments: {broll_completed}/{len(broll_segments)} completed")
    
    # Display assembly sequence
    st.subheader("Assembly Sequence")
    
    # Add a toggle for manual sequence editing
    enable_manual_editing = st.toggle("Enable Manual Sequence Editor", 
                                     value=st.session_state.get("enable_manual_editing", False),
                                     key="enable_manual_editing_toggle")
    st.session_state.enable_manual_editing = enable_manual_editing
    
    # Create assembly sequence if not already created
    if "sequence" not in st.session_state.video_assembly or not st.session_state.video_assembly["sequence"]:
        sequence_result = create_assembly_sequence()
        if sequence_result["status"] == "success":
            st.session_state.video_assembly["sequence"] = sequence_result["sequence"]
        else:
            st.error(sequence_result["message"])
            st.stop()
    
    # If sequence exists but doesn't match the current selection, regenerate it
    # Only if manual editing is not enabled
    if not enable_manual_editing:
        selected_sequence = st.session_state.get("selected_sequence", "")
        if selected_sequence != st.session_state.video_assembly.get("selected_sequence", ""):
            sequence_result = create_assembly_sequence()
            if sequence_result["status"] == "success":
                st.session_state.video_assembly["sequence"] = sequence_result["sequence"]
                st.session_state.video_assembly["selected_sequence"] = selected_sequence
            else:
                st.error(sequence_result["message"])
                st.stop()
    
    # Manual sequence editor
    if enable_manual_editing:
        st.markdown("### Manual Sequence Editor")
        st.markdown("Arrange your segments by dragging and dropping them in the desired order. "
                    "The audio from A-Roll segments will be preserved regardless of visual placement.")
        
        # Initialize available segments data if not already available
        if "available_segments" not in st.session_state:
            # Load content status
            content_status = load_content_status()
            if not content_status:
                st.error("Could not load content status. Please complete the Content Production step first.")
                st.stop()
                
            aroll_segments = content_status.get("aroll", {})
            broll_segments = content_status.get("broll", {})
            
            if not aroll_segments:
                st.error("No A-Roll segments found. Please complete the Content Production step first.")
                st.stop()
            
            # Create lists of available segments
            aroll_items = []
            for segment_id, segment_data in aroll_segments.items():
                segment_num = int(segment_id.split("_")[-1])
                filepath = get_aroll_filepath(segment_id, segment_data)
                if filepath:
                    aroll_items.append({
                        "segment_id": segment_id,
                        "segment_num": segment_num,
                        "filepath": filepath,
                        "type": "aroll"
                    })
            
            broll_items = []
            for segment_id, segment_data in broll_segments.items():
                segment_num = int(segment_id.split("_")[-1])
                filepath = segment_data.get("file_path", "")
                if filepath and os.path.exists(filepath):
                    broll_items.append({
                        "segment_id": segment_id,
                        "segment_num": segment_num,
                        "filepath": filepath,
                        "type": "broll"
                    })
            
            # Sort by segment number
            aroll_items.sort(key=lambda x: x["segment_num"])
            broll_items.sort(key=lambda x: x["segment_num"])
            
            if not aroll_items:
                st.error("No valid A-Roll files found. Please check Content Production status.")
                st.stop()
                
            st.session_state.available_segments = {
                "aroll": aroll_items,
                "broll": broll_items
            }
        
        # Helpful instruction message when first using the editor
        if st.session_state.get("first_time_manual_edit", True):
            st.info("""
            **How to use the manual editor:**
            1. Add segments using the buttons on the left panel
            2. Rearrange them using the arrows
            3. Click 'Apply Manual Sequence' when done
            
            You can create any combination of A-Roll videos and B-Roll videos with A-Roll audio.
            """)
            st.session_state.first_time_manual_edit = False
        
        # If we don't have a manual sequence yet, initialize it based on the current sequence
        if "manual_sequence" not in st.session_state:
            st.session_state.manual_sequence = []
            # Get the current sequence - either from session state or generate a new one
            if ("sequence" in st.session_state.video_assembly and 
                st.session_state.video_assembly["sequence"]):
                sequence = st.session_state.video_assembly["sequence"]
            else:
                # Generate a default sequence
                sequence_result = create_assembly_sequence()
                if sequence_result["status"] == "success":
                    sequence = sequence_result["sequence"]
                    st.session_state.video_assembly["sequence"] = sequence
                else:
                    # Handle error by showing a message and providing an empty sequence
                    st.error(f"Could not generate initial sequence: {sequence_result.get('message', 'Unknown error')}")
                    st.info("Please add segments manually using the controls below.")
                    sequence = []
            
            # Populate manual sequence from the sequence
            for item in sequence:
                if item["type"] == "aroll_full":
                    segment_id = item["segment_id"]
                    segment_num = int(segment_id.split("_")[-1])
                    st.session_state.manual_sequence.append({
                        "type": "aroll_full",
                        "aroll_segment_id": segment_id,
                        "aroll_segment_num": segment_num,
                        "aroll_path": item["aroll_path"]
                    })
                elif item["type"] == "broll_with_aroll_audio":
                    aroll_segment_id = item["segment_id"]
                    broll_segment_id = item["broll_id"]
                    aroll_segment_num = int(aroll_segment_id.split("_")[-1])
                    broll_segment_num = int(broll_segment_id.split("_")[-1])
                    st.session_state.manual_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_segment_id": aroll_segment_id,
                        "broll_segment_id": broll_segment_id,
                        "aroll_segment_num": aroll_segment_num,
                        "broll_segment_num": broll_segment_num,
                        "aroll_path": item["aroll_path"],
                        "broll_path": item["broll_path"]
                    })
        
        # Create two columns: one for available segments, one for sequence
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.markdown("#### Available Segments")
            
            # A-Roll segments
            st.markdown("**A-Roll Segments**")
            for item in st.session_state.available_segments["aroll"]:
                segment_num = item["segment_num"]
                segment_id = item["segment_id"]
                
                # Create buttons for adding segments
                if st.button(f"Add A-Roll {segment_num + 1}", key=f"add_aroll_{segment_num}"):
                    # Find the corresponding aroll item
                    aroll_path = item["filepath"]
                    
                    # Add to manual sequence
                    st.session_state.manual_sequence.append({
                        "type": "aroll_full",
                        "aroll_segment_id": segment_id,
                        "aroll_segment_num": segment_num,
                        "aroll_path": aroll_path
                    })
                    st.rerun()
            
            # B-Roll segments with A-Roll audio selection
            st.markdown("**B-Roll Segments**")
            for b_item in st.session_state.available_segments["broll"]:
                b_segment_num = b_item["segment_num"]
                b_segment_id = b_item["segment_id"]
                b_filepath = b_item["filepath"]
                
                # Add selection for which A-Roll audio to use
                aroll_options = [f"A-Roll {a['segment_num'] + 1}" for a in st.session_state.available_segments["aroll"]]
                selected_aroll = st.selectbox(
                    f"Audio for B-Roll {b_segment_num + 1}:",
                    aroll_options,
                    key=f"aroll_select_{b_segment_num}"
                )
                
                # Get the selected A-Roll index
                selected_aroll_num = int(selected_aroll.split(" ")[-1]) - 1
                
                # Find corresponding A-Roll
                aroll_item = next((a for a in st.session_state.available_segments["aroll"] 
                                  if a["segment_num"] == selected_aroll_num), None)
                
                if aroll_item:
                    a_segment_id = aroll_item["segment_id"]
                    a_segment_num = aroll_item["segment_num"]
                    a_filepath = aroll_item["filepath"]
                    
                    # Button to add B-Roll with A-Roll audio
                    if st.button(f"Add B-Roll {b_segment_num + 1}", key=f"add_broll_{b_segment_num}"):
                        st.session_state.manual_sequence.append({
                            "type": "broll_with_aroll_audio",
                            "aroll_segment_id": a_segment_id,
                            "broll_segment_id": b_segment_id,
                            "aroll_segment_num": a_segment_num,
                            "broll_segment_num": b_segment_num,
                            "aroll_path": a_filepath,
                            "broll_path": b_filepath
                        })
                        st.rerun()
        
        with col2:
            st.markdown("#### Current Sequence")
            st.markdown("Drag and drop segments to rearrange. The final video will follow this order.")
            
            # Display the current manual sequence
            if st.session_state.manual_sequence:
                # Use columns to create a row for each segment with buttons
                for i, item in enumerate(st.session_state.manual_sequence):
                    cols = st.columns([3, 1, 1, 1])
                    
                    # Display segment info
                    if item["type"] == "aroll_full":
                        segment_num = item["aroll_segment_num"]
                        cols[0].markdown(
                            f"""
                            <div style="text-align:center; border:2px solid #4CAF50; padding:8px; border-radius:5px; background-color:#E8F5E9;">
                            <strong>A-Roll {segment_num + 1}</strong><br>
                            <small>Full A-Roll segment</small>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    else:  # broll_with_aroll_audio
                        a_segment_num = item["aroll_segment_num"]
                        b_segment_num = item["broll_segment_num"]
                        cols[0].markdown(
                            f"""
                            <div style="text-align:center; border:2px solid #2196F3; padding:8px; border-radius:5px; background-color:#E3F2FD;">
                            <strong>B-Roll {b_segment_num + 1} + A-Roll {a_segment_num + 1} Audio</strong><br>
                            <small>B-Roll visuals with A-Roll audio</small>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    
                    # Move up button (except for first segment)
                    if i > 0:
                        if cols[1].button("↑", key=f"move_up_{i}"):
                            # Swap with previous segment
                            st.session_state.manual_sequence[i], st.session_state.manual_sequence[i-1] = \
                                st.session_state.manual_sequence[i-1], st.session_state.manual_sequence[i]
                            st.rerun()
                    
                    # Move down button (except for last segment)
                    if i < len(st.session_state.manual_sequence) - 1:
                        if cols[2].button("↓", key=f"move_down_{i}"):
                            # Swap with next segment
                            st.session_state.manual_sequence[i], st.session_state.manual_sequence[i+1] = \
                                st.session_state.manual_sequence[i+1], st.session_state.manual_sequence[i]
                            st.rerun()
                    
                    # Remove button
                    if cols[3].button("✖", key=f"remove_{i}"):
                        # Remove this segment
                        st.session_state.manual_sequence.pop(i)
                        st.rerun()
            else:
                st.info("No segments in the sequence yet. Add segments from the left panel.")
                
            # Button to clear the sequence
            if st.button("Clear Sequence", key="clear_sequence"):
                st.session_state.manual_sequence = []
                st.rerun()
                
            # Button to update the assembly sequence with the manual sequence
            if st.button("Apply Manual Sequence", key="apply_manual", type="primary"):
                # Check if we have any segments in the manual sequence
                if not st.session_state.manual_sequence:
                    st.error("Cannot apply an empty sequence. Please add at least one segment first.")
                    st.stop()
                    
                # Convert manual sequence to assembly sequence format
                assembly_sequence = []
                
                for item in st.session_state.manual_sequence:
                    if item["type"] == "aroll_full":
                        assembly_sequence.append({
                            "type": "aroll_full",
                            "aroll_path": item["aroll_path"],
                            "broll_path": None,
                            "segment_id": item["aroll_segment_id"]
                        })
                    else:  # broll_with_aroll_audio
                        assembly_sequence.append({
                            "type": "broll_with_aroll_audio",
                            "aroll_path": item["aroll_path"],
                            "broll_path": item["broll_path"],
                            "segment_id": item["aroll_segment_id"],
                            "broll_id": item["broll_segment_id"]
                        })
                
                # Update the sequence
                st.session_state.video_assembly["sequence"] = assembly_sequence
                st.session_state.video_assembly["selected_sequence"] = "Custom (Manual Arrangement)"
                
                # Success message
                st.success("Manual sequence applied!")
                st.rerun()
    
    # Display sequence preview
    st.markdown("The video will be assembled in the following sequence:")
    
    # Check if we have a valid sequence to display
    if not st.session_state.video_assembly.get("sequence"):
        st.warning("No sequence defined yet. Please select a sequence pattern or create a custom arrangement.")
    else:
        # Use cols to create a sequence preview
        cols = st.columns(min(8, len(st.session_state.video_assembly["sequence"])))
        
        # Create visual sequence preview with simple boxes
        for i, (item, col) in enumerate(zip(st.session_state.video_assembly["sequence"], cols)):
            segment_type = item["type"]
            segment_id = item.get("segment_id", "").split("_")[-1]  # Extract segment number
            
            if segment_type == "aroll_full":
                col.markdown(
                    f"""
                    <div style="text-align:center; border:2px solid #4CAF50; padding:8px; border-radius:5px; background-color:#E8F5E9;">
                    <strong>A-{int(segment_id) + 1}</strong><br>
                    <small>A-Roll video<br>A-Roll audio</small>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
            elif segment_type == "broll_with_aroll_audio":
                broll_id = item.get("broll_id", "").split("_")[-1]
                col.markdown(
                    f"""
                    <div style="text-align:center; border:2px solid #2196F3; padding:8px; border-radius:5px; background-color:#E3F2FD;">
                    <strong>B-{int(broll_id) + 1} + A-{int(segment_id) + 1}</strong><br>
                    <small>B-Roll video<br>A-Roll audio</small>
                    </div>
                    """, 
                    unsafe_allow_html=True
                )
        
        # Full text description of sequence
        st.markdown("#### Detailed Sequence:")
        for i, item in enumerate(st.session_state.video_assembly["sequence"]):
            if item["type"] == "aroll_full":
                segment_num = item['segment_id'].split('_')[-1]
                st.markdown(f"**{i+1}.** A-Roll Segment {int(segment_num) + 1} (full video and audio)")
            elif item["type"] == "broll_with_aroll_audio":
                broll_num = item['broll_id'].split('_')[-1]
                segment_num = item['segment_id'].split('_')[-1]
                st.markdown(f"**{i+1}.** B-Roll Segment {int(broll_num) + 1} visuals + A-Roll Segment {int(segment_num) + 1} audio")
    
    # Assembly options
    st.subheader("Assembly Options")
    resolution_options = ["1080x1920 (9:16)", "720x1280 (9:16)", "1920x1080 (16:9)"]
    st.session_state.selected_resolution = st.selectbox(
        "Output Resolution:", 
        resolution_options,
        index=resolution_options.index(st.session_state.get("selected_resolution", "1080x1920 (9:16)")),
        key="resolution_selectbox_secondary"
    )

    # Add a dependency check option
    if st.button("Check Dependencies", type="secondary", help="Check if all required packages are installed", key="check_dependencies_secondary"):
        with st.spinner("Checking dependencies..."):
            try:
                subprocess.run([sys.executable, "utils/video/dependencies.py"], check=True)
                st.success("All dependencies are installed!")
            except Exception as e:
                st.error(f"Error checking dependencies: {str(e)}")
                st.info("Please run `python utils/video/dependencies.py` manually to install required packages")