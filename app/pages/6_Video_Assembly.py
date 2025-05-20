import streamlit as st
import os
import sys
from pathlib import Path
import numpy as np
import time
from datetime import datetime
import cv2

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path")
    print("Successfully imported local modules")

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

# Function to create assembly sequence
def create_assembly_sequence(segments, content_status):
    """Create a sequence for video assembly based on available segments"""
    assembly_sequence = []
    aroll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
    broll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll"]
    
    # Count how many segments have completed content
    aroll_available = [f"segment_{i}" for i in range(len(aroll_segments)) 
                      if f"segment_{i}" in content_status["aroll"] and 
                      content_status["aroll"][f"segment_{i}"].get("status") == "complete"]
    
    broll_available = [f"segment_{i}" for i in range(len(broll_segments)) 
                      if f"segment_{i}" in content_status["broll"] and 
                      content_status["broll"][f"segment_{i}"].get("status") == "complete"]
    
    # Basic validation
    if not aroll_available:
        return {"status": "error", "message": "No completed A-Roll segments found."}
    
    # Create the assembly sequence
    # Start with the first A-Roll segment
    assembly_sequence.append({
        "type": "aroll_full",
        "segment_id": aroll_available[0],
        "index": 0,
        "file_path": content_status["aroll"][aroll_available[0]].get("file_path")
    })
    
    # Determine how many B-Roll + A-Roll audio segments we can create
    num_broll_with_aroll_audio = min(len(broll_available), len(aroll_available) - 1)
    
    # Add B-Roll visuals with A-Roll audio combinations
    for i in range(num_broll_with_aroll_audio):
        broll_seg_id = broll_available[i]
        aroll_seg_id = aroll_available[i + 1]  # Skip the first A-Roll as it's used fully
        
        assembly_sequence.append({
            "type": "broll_with_aroll_audio",
            "broll_segment_id": broll_seg_id,
            "aroll_segment_id": aroll_seg_id,
            "broll_index": i,
            "aroll_index": i + 1,
            "broll_file_path": content_status["broll"][broll_seg_id].get("file_path"),
            "aroll_file_path": content_status["aroll"][aroll_seg_id].get("file_path")
        })
    
    # Add remaining A-Roll segments (if any)
    for i in range(num_broll_with_aroll_audio + 1, len(aroll_available)):
        aroll_seg_id = aroll_available[i]
        
        assembly_sequence.append({
            "type": "aroll_full",
            "segment_id": aroll_seg_id,
            "index": i,
            "file_path": content_status["aroll"][aroll_seg_id].get("file_path")
        })
    
    return {"status": "success", "sequence": assembly_sequence}

# Function to assemble video based on sequence
def assemble_video(sequence, target_resolution=(1080, 1920)):
    """Assemble video clips according to the sequence"""
    # Check if MoviePy is available first
    if not MOVIEPY_AVAILABLE:
        st.error("Cannot assemble video: MoviePy is not available.")
        return None
        
    try:
        clips = []
        missing_files = []
        
        for item in sequence:
            if item["type"] == "aroll_full":
                # Full A-Roll segment (video + audio)
                file_path = item["file_path"]
                if os.path.exists(file_path):
                    clip = mp.VideoFileClip(file_path)
                    # Resize to target resolution
                    clip = resize_video(clip, target_resolution)
                    clips.append(clip)
                else:
                    missing_files.append(f"A-Roll file not found: {file_path}")
            
            elif item["type"] == "broll_with_aroll_audio":
                # B-Roll video with A-Roll audio
                broll_path = item["broll_file_path"]
                aroll_path = item["aroll_file_path"]
                
                if not os.path.exists(broll_path):
                    missing_files.append(f"B-Roll file not found: {broll_path}")
                    continue
                
                if not os.path.exists(aroll_path):
                    missing_files.append(f"A-Roll file not found: {aroll_path}")
                    continue
                
                # Check if B-Roll is an image or video
                is_image = broll_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                
                try:
                    if is_image:
                        # Load the image as a video clip with A-Roll duration
                        aroll_clip = mp.VideoFileClip(aroll_path)
                        broll_clip = mp.ImageClip(broll_path, duration=aroll_clip.duration)
                        aroll_clip.close()
                    else:
                        # Load B-Roll video
                        broll_clip = mp.VideoFileClip(broll_path)
                        
                        # Get A-Roll video to determine duration
                        aroll_clip = mp.VideoFileClip(aroll_path)
                        
                        # If B-Roll is shorter than A-Roll, loop it
                        if broll_clip.duration < aroll_clip.duration:
                            broll_clip = broll_clip.loop(duration=aroll_clip.duration)
                        # If B-Roll is longer than A-Roll, trim it
                        elif broll_clip.duration > aroll_clip.duration:
                            broll_clip = broll_clip.subclip(0, aroll_clip.duration)
                        
                        aroll_clip.close()
                    
                    # Resize B-Roll to target resolution
                    broll_clip = resize_video(broll_clip, target_resolution)
                    
                    # Extract audio from A-Roll
                    aroll_clip = mp.VideoFileClip(aroll_path)
                    aroll_audio = aroll_clip.audio
                    
                    # Set A-Roll audio to B-Roll clip
                    broll_clip = broll_clip.set_audio(aroll_audio)
                    
                    clips.append(broll_clip)
                    aroll_clip.close()
                except Exception as clip_error:
                    st.error(f"Error processing clips: {str(clip_error)}")
                    # Clean up any open clips
                    try:
                        if 'aroll_clip' in locals() and aroll_clip is not None:
                            aroll_clip.close()
                        if 'broll_clip' in locals() and broll_clip is not None:
                            broll_clip.close()
                    except:
                        pass
        
        # Check if we have missing files
        if missing_files:
            for error in missing_files:
                st.error(error)
            return None
            
        # Check if we have clips to concatenate
        if not clips:
            st.error("No valid clips were created. Assembly cannot proceed.")
            return None
            
        # Concatenate all clips
        final_clip = mp.concatenate_videoclips(clips)
        
        # Create output directory if it doesn't exist
        output_dir = project_path / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate output filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(output_dir / f"assembled_video_{timestamp}.mp4")
        
        # Write final video
        st.info("Rendering final video... This may take a while.")
        progress_text = st.empty()
        
        # MoviePy progress callback
        def write_progress(t, total_time):
            progress = min(100, int(t * 100 / total_time))
            progress_text.text(f"Rendering video: {progress}% complete")
        
        # Write final video with progress callback
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            threads=4,
            fps=30,
            logger=write_progress
        )
        
        # Clean up
        for clip in clips:
            clip.close()
        final_clip.close()
        
        return output_path
    
    except Exception as e:
        st.error(f"Error during video assembly: {str(e)}")
        # Make sure we clean up any open clips
        if 'clips' in locals():
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass
        return None

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
        sequence_result = create_assembly_sequence(segments, content_status)
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
            st.markdown(f"**{i+1}.** A-Roll Segment {item['index'] + 1} (full video and audio)")
        elif item["type"] == "broll_with_aroll_audio":
            st.markdown(f"**{i+1}.** B-Roll Segment {item['broll_index'] + 1} visuals + A-Roll Segment {item['aroll_index'] + 1} audio")
    
    # Assembly options
    st.subheader("Assembly Options")
    resolution_options = ["1080x1920 (9:16)", "720x1280 (9:16)", "1920x1080 (16:9)"]
    selected_resolution = st.selectbox("Output Resolution:", resolution_options)
    
    # Parse resolution
    width, height = map(int, selected_resolution.split(" ")[0].split("x"))
    
    # Assembly button
    if st.button("🎬 Assemble Video", type="primary", use_container_width=True):
        with st.spinner("Assembling video, please wait..."):
            st.session_state.video_assembly["status"] = "processing"
            
            # Perform video assembly
            output_path = assemble_video(st.session_state.video_assembly["sequence"], target_resolution=(width, height))
            
            if output_path and os.path.exists(output_path):
                st.session_state.video_assembly["status"] = "complete"
                st.session_state.video_assembly["output_path"] = output_path
                
                # Mark step as complete
                mark_step_complete("video_assembly")
                
                st.success(f"Video assembled successfully! Saved to: {output_path}")
                st.rerun()
            else:
                st.session_state.video_assembly["status"] = "error"
                st.session_state.video_assembly["error"] = "Failed to assemble video. Check the logs for details."
                st.error("Failed to assemble video. Check the logs for details.")
    
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