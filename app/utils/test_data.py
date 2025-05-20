import os
from pathlib import Path
import numpy as np
import time
import cv2
from moviepy.editor import VideoClip, AudioClip
import moviepy.editor as mp

def create_dummy_video(output_path, duration=3, fps=30, size=(640, 480), text=None):
    """
    Create a dummy video file with optional text overlay for testing purposes.
    
    Args:
        output_path: Path where the video will be saved
        duration: Duration of the video in seconds
        fps: Frames per second
        size: Size of the video (width, height)
        text: Optional text to display in the video
    
    Returns:
        Path to the created video file
    """
    try:
        # Make sure the directory exists
        output_dir = os.path.dirname(output_path)
        os.makedirs(output_dir, exist_ok=True)
        
        # Create a function that returns a frame at time t
        def make_frame(t):
            # Create a colored background that changes over time
            # Use HSV color space for smooth transitions
            h = int(t * 30) % 180  # Hue cycles through colors
            frame = np.zeros((size[1], size[0], 3), dtype=np.uint8)
            frame[:] = cv2.cvtColor(np.array([[[h, 255, 230]]], dtype=np.uint8), cv2.COLOR_HSV2RGB)
            
            # Add text if specified
            if text:
                # Determine text properties
                font = cv2.FONT_HERSHEY_SIMPLEX
                font_scale = 1.0
                font_color = (255, 255, 255)
                thickness = 2
                
                # Get text size to center it
                text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
                text_x = (frame.shape[1] - text_size[0]) // 2
                text_y = (frame.shape[0] + text_size[1]) // 2
                
                # Add text to the frame
                cv2.putText(frame, text, (text_x, text_y), font, font_scale, font_color, thickness)
                
                # Add a timestamp
                timestamp = f"Time: {t:.1f}s"
                cv2.putText(frame, timestamp, (10, 30), font, 0.5, font_color, 1)
            
            return frame
        
        # Create a function that generates audio at time t
        def make_audio(t):
            # Create a simple sine wave at 440Hz
            frequency = 440 + t * 10  # Increasing frequency over time
            return 0.5 * np.sin(2 * np.pi * frequency * t)
        
        # Create the video clip
        video_clip = VideoClip(make_frame, duration=duration)
        
        # Create audio clip
        audio_clip = AudioClip(make_audio, duration=duration, fps=44100)
        
        # Combine video and audio
        final_clip = video_clip.set_audio(audio_clip)
        
        # Write the video file
        final_clip.write_videofile(output_path, fps=fps, codec='libx264', audio_codec='aac')
        
        print(f"Created dummy video at {output_path}")
        return output_path
        
    except Exception as e:
        print(f"Error creating dummy video: {e}")
        return None

def generate_test_aroll_files(project_path, segment_ids=None):
    """
    Generate dummy A-Roll files for testing the video assembly functionality.
    
    Args:
        project_path: Base path for the project
        segment_ids: Dictionary of segment IDs to use for filenames
    
    Returns:
        List of paths to the created video files
    """
    if segment_ids is None:
        segment_ids = {
            "segment_0": "5169ef5a328149a8b13c365ee7060106",
            "segment_1": "aed87db0234e4965825c7ee4c1067467",
            "segment_2": "e7d47355c21e4190bad8752c799343ee",
            "segment_3": "36064085e2a240768a8368bc6a911aea"
        }
    
    # Create media directory if it doesn't exist
    media_dir = Path(project_path) / "media" / "aroll"
    media_dir.mkdir(parents=True, exist_ok=True)
    
    created_files = []
    
    # Generate a video file for each segment
    for segment_id, full_id in segment_ids.items():
        # Use a shortened version of the ID for the filename
        short_id = full_id[:8]
        
        # Create the output path
        output_path = str(media_dir / f"fetched_aroll_{segment_id}_{short_id}.mp4")
        
        # Create a test video
        segment_num = int(segment_id.split('_')[1]) + 1
        result = create_dummy_video(
            output_path, 
            duration=5,
            size=(640, 1280),  # 9:16 aspect ratio for shorts
            text=f"A-Roll Segment {segment_num}\nID: {short_id}"
        )
        
        if result:
            created_files.append(result)
    
    return created_files

def generate_test_broll_files(project_path, num_segments=3):
    """
    Generate dummy B-Roll files for testing the video assembly functionality.
    
    Args:
        project_path: Base path for the project
        num_segments: Number of B-Roll segments to generate
    
    Returns:
        List of paths to the created video files
    """
    # Create media directory if it doesn't exist
    media_dir = Path(project_path) / "media" / "broll"
    media_dir.mkdir(parents=True, exist_ok=True)
    
    created_files = []
    
    # Generate video files
    for i in range(num_segments):
        segment_id = f"segment_{i}"
        
        # Create the output path
        output_path = str(media_dir / f"generated_broll_{segment_id}.mp4")
        
        # Create a test video with a colored background and text
        result = create_dummy_video(
            output_path, 
            duration=5,
            size=(640, 1280),  # 9:16 aspect ratio for shorts
            text=f"B-Roll Segment {i+1}"
        )
        
        if result:
            created_files.append(result)
    
    return created_files

if __name__ == "__main__":
    # This allows running this script directly to generate test files
    import sys
    
    # Default project path is the current directory's parent
    project_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Generate test files
    print(f"Generating test A-Roll files in {project_path}")
    aroll_files = generate_test_aroll_files(project_path)
    print(f"Created {len(aroll_files)} A-Roll files")
    
    print(f"Generating test B-Roll files in {project_path}")
    broll_files = generate_test_broll_files(project_path)
    print(f"Created {len(broll_files)} B-Roll files") 