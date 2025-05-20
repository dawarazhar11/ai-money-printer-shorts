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
    
    # Create a sequence for assembly
    assembly_sequence = []
    
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
    
    # Segments 1-3: B-Roll visuals with A-Roll audio
    for i in range(1, 4):
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
    
    # Create assembly sequence
    if "sequence" not in st.session_state.video_assembly or not st.session_state.video_assembly["sequence"]:
        sequence_result = create_assembly_sequence()
        if sequence_result["status"] == "success":
            st.session_state.video_assembly["sequence"] = sequence_result["sequence"]
        else:
            st.error(sequence_result["message"])
            st.stop()
    
    # Display assembly sequence
    st.subheader("Assembly Sequence")
    st.markdown("The video will be assembled in the following sequence:")
    
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

    # Assembly button
    if st.button("🎬 Assemble Video", type="primary", use_container_width=True, key="assemble_video_secondary"):
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