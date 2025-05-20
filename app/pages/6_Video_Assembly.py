import streamlit as st
import os
import sys
from pathlib import Path
import numpy as np
import time
from datetime import datetime
import cv2
import traceback
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import io
import base64
from matplotlib.figure import Figure

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path")
    print("Successfully imported local modules")

# Define render_sequence_timeline function here, before it's needed
def render_sequence_timeline(sequence):
    """
    Render a timeline visualization of the video sequence showing
    how segments are arranged and where audio comes from
    
    Args:
        sequence: List of video segments to assemble
        
    Returns:
        str: Base64 encoded image of the timeline
    """
    if not sequence:
        return None
    
    fig, ax = plt.subplots(figsize=(12, 4))
    
    # Track durations and start times
    current_time = 0
    y_positions = {"video": 0.6, "audio": 0.2}
    colors = {
        "aroll_video": "#4CAF50",  # Green
        "broll_video": "#2196F3",  # Blue
        "aroll_audio": "#FF9800",  # Orange
    }
    
    # Set up the plot
    ax.set_ylim(0, 1)
    ax.set_xlim(0, 30)  # Adjust based on expected total duration
    ax.set_xlabel("Time (seconds)")
    ax.set_yticks([y_positions["video"], y_positions["audio"]])
    ax.set_yticklabels(["Video", "Audio"])
    ax.grid(axis="x", linestyle="--", alpha=0.7)
    ax.set_title("Sequence Timeline")
    
    # Track start times for each segment
    start_times = []
    segment_durations = []
    
    # Estimate durations (in practice, you would get these from the actual video files)
    # For this visualization, we'll use average durations
    avg_duration = 7  # seconds per segment - typical short segment
    
    # Loop through sequences and draw rectangles for each segment
    for i, item in enumerate(sequence):
        segment_id = item.get("segment_id", f"segment_{i}")
        segment_duration = avg_duration  # In a real implementation, get actual duration
        segment_durations.append(segment_duration)
        start_times.append(current_time)
        
        # Draw video track
        if item["type"] == "aroll_full":
            # A-Roll video track
            video_rect = patches.Rectangle(
                (current_time, y_positions["video"] - 0.15), 
                segment_duration, 
                0.3, 
                facecolor=colors["aroll_video"],
                alpha=0.8,
                label="A-Roll Video" if i == 0 else None
            )
            ax.add_patch(video_rect)
            ax.text(
                current_time + segment_duration / 2, 
                y_positions["video"], 
                f"A-{segment_id.split('_')[-1]}", 
                ha="center", 
                va="center",
                color="white",
                fontweight="bold"
            )
            
            # A-Roll audio track (same source)
            audio_rect = patches.Rectangle(
                (current_time, y_positions["audio"] - 0.15), 
                segment_duration, 
                0.3, 
                facecolor=colors["aroll_audio"],
                alpha=0.8,
                label="A-Roll Audio" if i == 0 else None
            )
            ax.add_patch(audio_rect)
            ax.text(
                current_time + segment_duration / 2, 
                y_positions["audio"], 
                f"A-{segment_id.split('_')[-1]}", 
                ha="center", 
                va="center",
                color="black",
                fontweight="bold"
            )
        else:  # broll_with_aroll_audio
            broll_id = item.get("broll_id", "").split("_")[-1]
            # B-Roll video track
            video_rect = patches.Rectangle(
                (current_time, y_positions["video"] - 0.15), 
                segment_duration, 
                0.3, 
                facecolor=colors["broll_video"],
                alpha=0.8,
                label="B-Roll Video" if i == 0 or (i > 0 and sequence[i-1]["type"] != "broll_with_aroll_audio") else None
            )
            ax.add_patch(video_rect)
            ax.text(
                current_time + segment_duration / 2, 
                y_positions["video"], 
                f"B-{broll_id}", 
                ha="center", 
                va="center",
                color="white",
                fontweight="bold"
            )
            
            # A-Roll audio track
            audio_rect = patches.Rectangle(
                (current_time, y_positions["audio"] - 0.15), 
                segment_duration, 
                0.3, 
                facecolor=colors["aroll_audio"],
                alpha=0.8,
                label="A-Roll Audio" if i == 0 or (i > 0 and sequence[i-1]["type"] != "broll_with_aroll_audio") else None
            )
            ax.add_patch(audio_rect)
            ax.text(
                current_time + segment_duration / 2, 
                y_positions["audio"], 
                f"A-{segment_id.split('_')[-1]}", 
                ha="center", 
                va="center",
                color="black",
                fontweight="bold"
            )
        
        current_time += segment_duration
    
    # Adjust the x-axis to fit the content
    ax.set_xlim(0, current_time + 2)
    
    # Add legend
    handles, labels = ax.get_legend_handles_labels()
    by_label = dict(zip(labels, handles))
    ax.legend(by_label.values(), by_label.keys(), loc="upper right")
    
    # Convert plot to image
    buf = io.BytesIO()
    fig.tight_layout()
    plt.savefig(buf, format="png", dpi=100)
    plt.close(fig)
    
    # Encode the image to base64 string
    buf.seek(0)
    img_str = base64.b64encode(buf.read()).decode("utf-8")
    
    return img_str

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

# Add utils.video.broll_defaults import
from utils.video.broll_defaults import apply_default_broll_ids, update_session_state_with_defaults

# Set page configuration
st.set_page_config(
    page_title="Video Assembly | AI Money Printer",
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
        
        # If the file path is just a filename without directory, prepend media/a-roll/
        if not os.path.dirname(file_path):
            media_path = f"media/a-roll/{file_path}"
            if os.path.exists(media_path):
                print(f"Found A-Roll file: {media_path}")
                return media_path
        
        # Check if the provided path exists directly
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

def get_broll_filepath(segment_id, segment_data):
    """
    Get the filepath for a B-Roll segment, supporting different path formats
    
    Args:
        segment_id: ID of the segment (e.g., 'segment_0')
        segment_data: Data for the segment
        
    Returns:
        str: Path to the B-Roll file if found, None otherwise
    """
    # Check the file path in the content status
    if "file_path" in segment_data:
        file_path = segment_data["file_path"]
        
        # If the file path is just a filename without directory, prepend media/b-roll/
        if not os.path.dirname(file_path):
            media_path = f"media/b-roll/{file_path}"
            if os.path.exists(media_path):
                print(f"Found B-Roll file: {media_path}")
                return media_path
        
        # Check if the provided path exists directly
        if os.path.exists(file_path):
            return file_path
    
    # Try alternative formats if the primary file path doesn't exist
    segment_num = segment_id.split('_')[-1]
    prompt_id = segment_data.get('prompt_id', '')
    
    # Different file naming patterns to try
    patterns = [
        # Common formats
        f"media/b-roll/broll_segment_{segment_num}.mp4",
        f"{app_root}/media/b-roll/broll_segment_{segment_num}.mp4",
        f"media/b-roll/fetched_broll_segment_{segment_num}.mp4",
        f"{app_root}/media/b-roll/fetched_broll_segment_{segment_num}.mp4"
    ]
    
    # Try each pattern
    for pattern in patterns:
        if os.path.exists(pattern):
            print(f"Found B-Roll file: {pattern}")
            return pattern
            
    print(f"B-Roll file not found for {segment_id}")
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
    
    # If Custom is selected and we already have a manually created sequence, preserve it
    if "Custom" in selected_sequence and "video_assembly" in st.session_state and "sequence" in st.session_state.video_assembly:
        existing_sequence = st.session_state.video_assembly.get("sequence", [])
        if existing_sequence:
            return {"status": "success", "sequence": existing_sequence}
    
    # Create a sequence for assembly based on the selected pattern
    assembly_sequence = []
    
    # Check how many segments we have
    total_aroll_segments = len(aroll_segments)
    total_broll_segments = len(broll_segments)
    
    if total_aroll_segments == 0:
        return {"status": "error", "message": "No A-Roll segments found"}
    
    # B-Roll Full (all visuals are B-Roll with A-Roll audio)
    if "B-Roll Full" in selected_sequence:
        # All segments use B-Roll visuals with A-Roll audio
        # Track which A-Roll segments have been used to prevent duplicates
        used_aroll_segments = set()
        
        # First arrange all A-Roll segments sequentially, with B-Roll visuals
        for i in range(total_aroll_segments):
            aroll_segment_id = f"segment_{i}"
            
            # Skip if this A-Roll segment was already used
            if aroll_segment_id in used_aroll_segments:
                print(f"Skipping duplicate A-Roll segment {i} to prevent audio overlap")
                continue
                
            # Use the appropriate B-Roll segment or cycle through available ones
            # To prevent audio overlaps, each A-Roll segment is used exactly once
            broll_index = i % total_broll_segments
            broll_segment_id = f"segment_{broll_index}"
            
            if aroll_segment_id in aroll_segments and broll_segment_id in broll_segments:
                aroll_data = aroll_segments[aroll_segment_id]
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                broll_path = get_broll_filepath(broll_segment_id, broll_data)
                
                if aroll_path and broll_path:
                    print(f"Adding B-Roll segment {broll_index} with A-Roll segment {i}")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": aroll_segment_id,
                        "broll_id": broll_segment_id
                    })
                    # Mark this A-Roll segment as used
                    used_aroll_segments.add(aroll_segment_id)
                    
                    print(f"✅ Added audio segment {aroll_segment_id} to sequence position {len(assembly_sequence)}")
    # Standard pattern (original implementation)
    elif "Standard" in selected_sequence:
        # Track which A-Roll segments have been used to prevent duplicates
        used_aroll_segments = set()
        
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
                # Mark as used
                used_aroll_segments.add("segment_0")
            else:
                st.error(f"A-Roll file not found: {aroll_data.get('file_path', 'No path specified')}")
        
        # Middle segments: B-Roll visuals with A-Roll audio
        for i in range(1, total_aroll_segments - 1):
            aroll_segment_id = f"segment_{i}"
            
            # Skip if this A-Roll segment was already used
            if aroll_segment_id in used_aroll_segments:
                print(f"Skipping duplicate A-Roll segment {i} to prevent audio overlap")
                continue
                
            broll_segment_id = f"segment_{i-1}"  # B-Roll segments are named "segment_X" in content_status.json
            
            if aroll_segment_id in aroll_segments and broll_segment_id in broll_segments:
                aroll_data = aroll_segments[aroll_segment_id]
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                broll_path = get_broll_filepath(broll_segment_id, broll_data)
                
                if aroll_path and broll_path:
                    print(f"Adding B-Roll segment {i-1} with A-Roll segment {i}")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": aroll_segment_id,
                        "broll_id": broll_segment_id
                    })
                    # Mark as used
                    used_aroll_segments.add(aroll_segment_id)
                else:
                    if not aroll_path:
                        st.error(f"A-Roll file not found for {aroll_segment_id}")
                    if not broll_path:
                        st.error(f"B-Roll file not found for {broll_segment_id}")
        
        # Last segment is A-Roll only
        last_segment_id = f"segment_{total_aroll_segments - 1}"
        
        # Skip if this A-Roll segment was already used
        if last_segment_id not in used_aroll_segments and last_segment_id in aroll_segments:
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
                # Mark as used
                used_aroll_segments.add(last_segment_id)
    
    # A-Roll Bookends pattern
    elif "Bookends" in selected_sequence:
        # Track which A-Roll segments have been used to prevent duplicates
        used_aroll_segments = set()
        
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
                # Mark as used
                used_aroll_segments.add("segment_0")
        
        # All middle segments use B-Roll visuals with A-Roll audio
        for i in range(1, total_aroll_segments - 1):
            aroll_segment_id = f"segment_{i}"
            
            # Skip if this A-Roll segment was already used
            if aroll_segment_id in used_aroll_segments:
                print(f"Skipping duplicate A-Roll segment {i} to prevent audio overlap")
                continue
                
            # Use the appropriate B-Roll segment or cycle through available ones
            broll_index = (i - 1) % total_broll_segments
            broll_segment_id = f"segment_{broll_index}"
            
            if aroll_segment_id in aroll_segments and broll_segment_id in broll_segments:
                aroll_data = aroll_segments[aroll_segment_id]
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                broll_path = get_broll_filepath(broll_segment_id, broll_data)
                
                if aroll_path and broll_path:
                    print(f"Adding B-Roll segment {broll_index} with A-Roll segment {i}")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": aroll_segment_id,
                        "broll_id": broll_segment_id
                    })
                    # Mark as used
                    used_aroll_segments.add(aroll_segment_id)
            
        # Last segment is A-Roll only
        last_segment_id = f"segment_{total_aroll_segments - 1}"
        
        # Skip if this A-Roll segment was already used
        if last_segment_id not in used_aroll_segments and last_segment_id in aroll_segments:
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
                # Mark as used
                used_aroll_segments.add(last_segment_id)
    
    # A-Roll Sandwich pattern (A-Roll at start, middle, and end)
    elif "Sandwich" in selected_sequence:
        # Track which A-Roll segments have been used to prevent duplicates
        used_aroll_segments = set()
        
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
            
            # Skip if this A-Roll segment was already used
            if aroll_segment_id in used_aroll_segments:
                print(f"Skipping duplicate A-Roll segment {i} to prevent audio overlap")
                continue
                
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
                        # Mark as used
                        used_aroll_segments.add(aroll_segment_id)
            # Otherwise use B-Roll with A-Roll audio
            else:
                # Use the appropriate B-Roll segment or cycle through available ones
                broll_index = (i - 1) % total_broll_segments
                broll_segment_id = f"segment_{broll_index}"
                
                if aroll_segment_id in aroll_segments and broll_segment_id in broll_segments:
                    aroll_data = aroll_segments[aroll_segment_id]
                    broll_data = broll_segments[broll_segment_id]
                    
                    aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                    broll_path = get_broll_filepath(broll_segment_id, broll_data)
                    
                    if aroll_path and broll_path:
                        print(f"Adding B-Roll segment {broll_index} with A-Roll segment {i}")
                        assembly_sequence.append({
                            "type": "broll_with_aroll_audio",
                            "aroll_path": aroll_path,
                            "broll_path": broll_path,
                            "segment_id": aroll_segment_id,
                            "broll_id": broll_segment_id
                        })
                        # Mark as used
                        used_aroll_segments.add(aroll_segment_id)
    
    # B-Roll Heavy (only first segment uses A-Roll visual)
    elif "B-Roll Heavy" in selected_sequence:
        # Track which A-Roll segments have been used to prevent duplicates
        used_aroll_segments = set()
        
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
                # Mark as used
                used_aroll_segments.add("segment_0")
        
        # All remaining segments use B-Roll visuals with A-Roll audio
        for i in range(1, total_aroll_segments):
            aroll_segment_id = f"segment_{i}"
            
            # Skip if this A-Roll segment was already used
            if aroll_segment_id in used_aroll_segments:
                print(f"Skipping duplicate A-Roll segment {i} to prevent audio overlap")
                continue
                
            # Use the appropriate B-Roll segment or cycle through available ones
            broll_index = (i - 1) % total_broll_segments
            broll_segment_id = f"segment_{broll_index}"
            
            if aroll_segment_id in aroll_segments and broll_segment_id in broll_segments:
                aroll_data = aroll_segments[aroll_segment_id]
                broll_data = broll_segments[broll_segment_id]
                
                aroll_path = get_aroll_filepath(aroll_segment_id, aroll_data)
                broll_path = get_broll_filepath(broll_segment_id, broll_data)
                
                if aroll_path and broll_path:
                    print(f"Adding B-Roll segment {broll_index} with A-Roll segment {i}")
                    assembly_sequence.append({
                        "type": "broll_with_aroll_audio",
                        "aroll_path": aroll_path,
                        "broll_path": broll_path,
                        "segment_id": aroll_segment_id,
                        "broll_id": broll_segment_id
                    })
                    # Mark as used
                    used_aroll_segments.add(aroll_segment_id)
    
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

def check_for_audio_overlaps(sequence):
    """
    Check for potential audio overlaps in the sequence and display warnings in UI
    
    Args:
        sequence: List of video segments to assemble
    """
    used_audio_segments = {}
    overlaps = []
    segment_details = []
    
    for i, item in enumerate(sequence):
        segment_id = item.get("segment_id", f"segment_{i}")
        
        # Track which A-Roll audio segments are being used
        if segment_id in used_audio_segments:
            overlaps.append({
                "segment": i+1, 
                "audio_id": segment_id,
                "previous_use": used_audio_segments[segment_id]["index"]+1,
                "previous_type": used_audio_segments[segment_id]["type"]
            })
            
            # Add this segment to the details with overlap flag
            segment_details.append({
                "index": i,
                "segment_id": segment_id,
                "type": item["type"],
                "has_overlap": True,
                "original_index": used_audio_segments[segment_id]["index"]
            })
        else:
            used_audio_segments[segment_id] = {
                "index": i,
                "type": item["type"]
            }
            
            # Add to details without overlap flag
            segment_details.append({
                "index": i,
                "segment_id": segment_id,
                "type": item["type"],
                "has_overlap": False
            })
    
    if overlaps:
        st.warning("⚠️ **Audio Overlap Warning**: Your sequence contains multiple uses of the same audio segments.", icon="⚠️")
        st.markdown("This may cause audio to be repeated or overlapped in your final video.")
        
        # Create a detailed timeline visualization
        st.markdown("### 🔊 Audio Track Sequence")
        st.markdown("The following shows your audio track sequence, with overlaps highlighted:")
        
        # Create a formatted table of segments
        segments_md = "| # | Segment ID | Type | Status |\n"
        segments_md += "| --- | --- | --- | --- |\n"
        
        for segment in segment_details:
            status = "⚠️ **OVERLAP**" if segment["has_overlap"] else "✅ OK"
            overlap_info = f" (duplicate of #{segment['original_index']+1})" if segment["has_overlap"] else ""
            type_display = "A-Roll Full" if segment["type"] == "aroll_full" else "B-Roll with A-Roll Audio"
            segments_md += f"| {segment['index']+1} | {segment['segment_id']} | {type_display} | {status}{overlap_info} |\n"
        
        st.markdown(segments_md)
        
        for overlap in overlaps:
            st.warning(f"**Segment {overlap['segment']}** uses the same audio ({overlap['audio_id']}) as segment {overlap['previous_use']}")
        
        st.markdown("""
        **To fix audio overlaps:**
        
        1. **Best solution:** Use the Custom arrangement to control exactly which audio segments are used
        2. Try a different sequence pattern that doesn't reuse audio segments
        3. Use "B-Roll Full" preset which is designed to ensure each A-Roll audio segment is used exactly once
        """)
        
        # Display additional debugging info in an expander
        with st.expander("Advanced Audio Overlap Analysis"):
            st.markdown(f"**Total segments:** {len(sequence)}")
            st.markdown(f"**Unique audio tracks:** {len(used_audio_segments)}")
            st.markdown(f"**Overlapping audio tracks:** {len(overlaps)}")
            
            # Display the actual sequence composition
            sequence_details = ""
            for i, item in enumerate(sequence):
                segment_id = item.get("segment_id", "unknown")
                type_str = item.get("type", "unknown")
                aroll_path = item.get("aroll_path", "none")
                broll_path = item.get("broll_path", "none")
                
                sequence_details += f"**Segment {i+1}:** {segment_id} ({type_str})\n"
                sequence_details += f"  - A-Roll: {os.path.basename(aroll_path)}\n"
                if broll_path != "none":
                    sequence_details += f"  - B-Roll: {os.path.basename(broll_path)}\n"
                sequence_details += "\n"
            
            st.markdown(sequence_details)
        
        return True
    return False

# Replace the assemble_video function to include fallback to simple_assembly
def assemble_video():
    """
    Assemble the final video from A-Roll and B-Roll segments
    """
    if not MOVIEPY_AVAILABLE:
        st.error("MoviePy is not available. Installing required packages...")
        st.info("Please run: `python utils/video/dependencies.py` to install required packages")
        return

    # If we're using Custom arrangement and already have a sequence, use it directly
    if ("Custom" in st.session_state.get("selected_sequence", "") and 
        "sequence" in st.session_state.video_assembly and 
        st.session_state.video_assembly["sequence"]):
        assembly_sequence = st.session_state.video_assembly["sequence"]
        # Verify the sequence has at least one item
        if not assembly_sequence:
            st.error("No valid segments found in the custom sequence. Please create a sequence first.")
            return
        sequence_result = {"status": "success", "sequence": assembly_sequence}
        print("Using existing custom sequence for assembly")
    else:
        # Get the assembly sequence
        sequence_result = create_assembly_sequence()
        
    if sequence_result["status"] != "success":
        st.error(sequence_result.get("message", "Failed to create assembly sequence"))
        return
        
    assembly_sequence = sequence_result["sequence"]
    
    # Check for audio overlaps and warn the user
    has_overlaps = check_for_audio_overlaps(assembly_sequence)
    if has_overlaps:
        continue_anyway = st.checkbox("Continue with assembly despite audio overlaps", value=False)
        if not continue_anyway:
            st.warning("Video assembly paused until audio overlaps are resolved or you choose to continue anyway.")
            return
    
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
    "B-Roll Full (All B-Roll visuals with A-Roll audio) - Prevents audio overlaps",
    "Custom (Manual Arrangement)"
]
st.session_state.selected_sequence = st.selectbox(
    "Sequence Pattern:", 
    sequence_options,
    index=sequence_options.index(st.session_state.get("selected_sequence", sequence_options[0])),
    key="sequence_selectbox"
)

# Add warning about audio overlaps in certain presets
if not "B-Roll Full" in st.session_state.selected_sequence and not "Custom" in st.session_state.selected_sequence:
    st.info("""
    ℹ️ **Note:** Some sequence patterns may cause audio overlaps if there are more A-Roll segments than B-Roll segments.
    If you experience audio overlaps, try the "B-Roll Full" preset or "Custom" arrangement for full control.
    """)

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
if st.button("Check Dependencies", type="secondary", help="Check if all required packages are installed", key="check_deps_main"):
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
                filepath = get_broll_filepath(segment_id, segment_data)
                if filepath:
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
                # Track audio segments to detect duplicates
                used_audio_segments = {}
                has_audio_overlaps = False
                
                # Use columns to create a row for each segment with buttons
                for i, item in enumerate(st.session_state.manual_sequence):
                    cols = st.columns([3, 1, 1, 1])
                    
                    # Check if this is an audio overlap
                    is_overlap = False
                    segment_id = None
                    
                    if item["type"] == "aroll_full":
                        segment_id = item["aroll_segment_id"]
                    else:  # broll_with_aroll_audio
                        segment_id = item["aroll_segment_id"]
                        
                    if segment_id in used_audio_segments:
                        is_overlap = True
                        has_audio_overlaps = True
                    else:
                        used_audio_segments[segment_id] = i
                    
                    # Display segment info with warning if it's an overlap
                    if item["type"] == "aroll_full":
                        segment_num = item["aroll_segment_num"]
                        
                        # Add warning color if this is an overlap
                        border_color = "#FF5733" if is_overlap else "#4CAF50"
                        bg_color = "#FFEBEE" if is_overlap else "#E8F5E9"
                        warning_text = "<br><small>⚠️ <strong>DUPLICATE AUDIO</strong></small>" if is_overlap else ""
                        
                        cols[0].markdown(
                            f"""
                            <div style="text-align:center; border:2px solid {border_color}; padding:8px; border-radius:5px; background-color:{bg_color};">
                            <strong>A-Roll {segment_num + 1}</strong><br>
                            <small>Full A-Roll segment{warning_text}</small>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                    else:  # broll_with_aroll_audio
                        a_segment_num = item["aroll_segment_num"]
                        b_segment_num = item["broll_segment_num"]
                        
                        # Add warning color if this is an overlap
                        border_color = "#FF5733" if is_overlap else "#2196F3"
                        bg_color = "#FFEBEE" if is_overlap else "#E3F2FD"
                        warning_text = "<br><small>⚠️ <strong>DUPLICATE AUDIO</strong></small>" if is_overlap else ""
                        
                        cols[0].markdown(
                            f"""
                            <div style="text-align:center; border:2px solid {border_color}; padding:8px; border-radius:5px; background-color:{bg_color};">
                            <strong>B-Roll {b_segment_num + 1} + A-Roll {a_segment_num + 1} Audio</strong><br>
                            <small>B-Roll visuals with A-Roll audio{warning_text}</small>
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
                
                # Show audio flow visualization if we have at least two segments
                if len(st.session_state.manual_sequence) >= 2:
                    st.markdown("### 🔊 Audio Flow Visualization")
                    st.markdown("This shows how audio flows through your sequence:")
                    
                    # Create a visual representation of the audio flow
                    audio_flow = ""
                    for i, item in enumerate(st.session_state.manual_sequence):
                        if item["type"] == "aroll_full":
                            segment_num = item["aroll_segment_num"]
                            segment_id = item["aroll_segment_id"]
                            
                            # Check if this is an audio overlap
                            if segment_id in used_audio_segments and used_audio_segments[segment_id] != i:
                                audio_flow += f"**[A-{segment_num+1}]** ⚠️ → "
                            else:
                                audio_flow += f"**[A-{segment_num+1}]** → "
                        else:  # broll_with_aroll_audio
                            a_segment_num = item["aroll_segment_num"]
                            segment_id = item["aroll_segment_id"]
                            
                            # Check if this is an audio overlap
                            if segment_id in used_audio_segments and used_audio_segments[segment_id] != i:
                                audio_flow += f"**[A-{a_segment_num+1}]** ⚠️ → "
                            else:
                                audio_flow += f"**[A-{a_segment_num+1}]** → "
                    
                    # Remove the last arrow
                    audio_flow = audio_flow[:-4]
                    
                    # Display the audio flow
                    st.markdown(audio_flow)
                    
                    # Show warning if there are audio overlaps
                    if has_audio_overlaps:
                        st.warning("⚠️ Your sequence contains duplicate audio segments that may cause audio overlaps. Items marked with ⚠️ use audio that appears earlier in the sequence.")
                
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
                    
                    # Make sure the sequence is immediately available for assembly
                    if assembly_sequence:
                        # Verify all paths exist
                        missing_files = []
                        for seq_item in assembly_sequence:
                            if "aroll_path" in seq_item and not os.path.exists(seq_item["aroll_path"]):
                                missing_files.append(f"A-Roll file not found: {seq_item['aroll_path']}")
                            if "broll_path" in seq_item and seq_item["broll_path"] and not os.path.exists(seq_item["broll_path"]):
                                missing_files.append(f"B-Roll file not found: {seq_item['broll_path']}")
                        
                        if missing_files:
                            st.error("Missing files in sequence:")
                            for msg in missing_files:
                                st.warning(msg)
                        else:
                            st.success("All files in sequence are valid!")
                    
                    st.rerun()
            else:
                st.info("No segments in the sequence yet. Add segments from the left panel.")
    
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
    
    # Show timeline visualization
    st.markdown("#### Timeline Visualization:")
    
    # Generate timeline visualization
    timeline_img = render_sequence_timeline(st.session_state.video_assembly["sequence"])
    
    if timeline_img:
        st.markdown(f"""
            <div style="text-align: center;">
                <img src="data:image/png;base64,{timeline_img}" style="max-width: 100%; height: auto;">
            </div>
            <p style="text-align: center; font-size: 0.8em; color: #666;">
                Timeline showing video and audio tracks. Green = A-Roll video, Blue = B-Roll video, Orange = A-Roll audio.
            </p>
        """, unsafe_allow_html=True)
        
        # Add note about potential audio overlaps
        st.markdown("""
            <div style="background-color: #f8f9fa; padding: 10px; border-radius: 5px; margin-top: 10px;">
                <p style="margin: 0; font-size: 0.9em;">
                    <strong>Note:</strong> If you notice audio overlaps or issues in the final video, try adjusting the sequence 
                    to ensure each A-Roll audio segment is used only once, or use the Custom Arrangement for more control.
                </p>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.info("Generate a sequence to view the timeline visualization.")

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
    if st.button("Check Dependencies", type="secondary", help="Check if all required packages are installed", key="check_deps_secondary"):
        with st.spinner("Checking dependencies..."):
            try:
                subprocess.run([sys.executable, "utils/video/dependencies.py"], check=True)
                st.success("All dependencies are installed!")
            except Exception as e:
                st.error(f"Error checking dependencies: {str(e)}")
                st.info("Please run `python utils/video/dependencies.py` manually to install required packages")

# Add call to apply default B-roll IDs in the initialization section
# ... existing code ...
# Initialize content status
if "content_status" not in st.session_state:
    content_status = load_content_status()
    if content_status:
        st.session_state.content_status = content_status
        
        # Apply default B-roll IDs to content status
        if apply_default_broll_ids(st.session_state.content_status):
            save_content_status()  # Save if changes were made
            
        # Update session state with default B-roll IDs
        update_session_state_with_defaults(st.session_state)
    else:
        st.session_state.content_status = {"aroll": {}, "broll": {}}