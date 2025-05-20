#!/usr/bin/env python3
import os
import sys
import traceback
from pathlib import Path
import time
from datetime import datetime
import json
import tempfile
import subprocess
import shutil

# Add the parent directory to the Python path to allow importing from app modules
app_root = Path(__file__).parent.parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path from assembly module")

# Import error handler decorator to gracefully handle errors in functions
def error_handler(func):
    """Decorator to handle errors gracefully"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"❌ Error in {func.__name__}: {str(e)}")
            print(f"Traceback: {traceback.format_exc()}")
            return {"status": "error", "message": str(e), "traceback": traceback.format_exc()}
    return wrapper

# Try to import MoviePy, if it fails we'll handle it gracefully
try:
    import moviepy.editor as mp
    from moviepy.video.fx import resize, speedx
    import numpy as np
    MOVIEPY_AVAILABLE = True
    print("✅ Successfully imported moviepy in assembly module")
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    print(f"❌ Error importing moviepy in assembly module: {str(e)}")
    print("Please run: python utils/video/dependencies.py to install required packages")

@error_handler
def check_file(file_path, file_type="video"):
    """
    Check if a file exists and is valid
    
    Args:
        file_path: Path to the file
        file_type: Type of file (video, image, audio)
        
    Returns:
        dict: Result containing status and additional info
    """
    if not file_path:
        return {"status": "error", "message": f"No {file_type} path provided"}
        
    if not os.path.exists(file_path):
        return {"status": "error", "message": f"{file_type.capitalize()} file not found: {file_path}"}
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return {"status": "error", "message": f"{file_type.capitalize()} file is empty: {file_path}"}
    
    # For video/audio files, validate they're proper media files
    if file_type in ["video", "audio"] and MOVIEPY_AVAILABLE:
        try:
            if file_type == "video":
                clip = mp.VideoFileClip(file_path)
                duration = clip.duration
                width, height = clip.size
                clip.close()
                return {
                    "status": "success", 
                    "path": file_path,
                    "size": file_size,
                    "duration": duration,
                    "width": width,
                    "height": height
                }
            elif file_type == "audio":
                clip = mp.AudioFileClip(file_path)
                duration = clip.duration
                clip.close()
                return {
                    "status": "success", 
                    "path": file_path,
                    "size": file_size,
                    "duration": duration
                }
        except Exception as e:
            return {
                "status": "error", 
                "message": f"Invalid {file_type} file: {file_path}", 
                "error": str(e)
            }
    
    # For image files or if MoviePy is not available
    return {"status": "success", "path": file_path, "size": file_size}

@error_handler
def resize_video(clip, target_resolution=(1080, 1920)):
    """
    Resize video clip to target resolution maintaining aspect ratio with padding
    
    Args:
        clip: MoviePy video clip
        target_resolution: Target resolution (width, height)
        
    Returns:
        Resized video clip
    """
    if not MOVIEPY_AVAILABLE:
        return None
    
    # Get original dimensions
    w, h = clip.size
    
    # Calculate target aspect ratio
    target_aspect = target_resolution[0] / target_resolution[1]  # width/height
    current_aspect = w / h
    
    try:
        if current_aspect > target_aspect:
            # Video is wider than target aspect ratio - fit to width
            new_width = target_resolution[0]
            new_height = int(new_width / current_aspect)
            resized_clip = clip.resize(width=new_width, height=new_height)
            
            # Add padding to top and bottom
            padding_top = (target_resolution[1] - new_height) // 2
            
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
    except Exception as e:
        print(f"❌ Error resizing video: {str(e)}")
        print(traceback.format_exc())
        # Return original clip if resize fails
        return clip

# Add this new function to validate audio
def has_valid_audio(clip):
    """Check if a clip has valid audio"""
    try:
        if clip.audio is None:
            print("Clip has no audio track")
            return False
            
        # Additional validation
        try:
            # Try to access a frame to check if audio is valid
            _ = clip.audio.get_frame(0)
            # Check if the audio has a duration
            if clip.audio.duration <= 0:
                print("Audio track has zero or negative duration")
                return False
            return True
        except (AttributeError, IOError, ValueError) as e:
            print(f"Audio validation error: {str(e)}")
            return False
    except Exception as e:
        print(f"Unexpected audio validation error: {str(e)}")
        return False

# Add this function after has_valid_audio and before extract_audio_track
def check_audio_overlaps(sequence):
    """
    Check for potential audio overlaps in the sequence
    
    Args:
        sequence: List of video segments to assemble
        
    Returns:
        dict: Result containing status and any overlap warnings
    """
    warnings = []
    used_audio_segments = {}
    
    for i, item in enumerate(sequence):
        segment_id = item.get("segment_id", f"segment_{i}")
        
        # Track which A-Roll audio segments are being used
        if segment_id in used_audio_segments:
            warnings.append(f"Segment {i+1}: Using same A-Roll audio ({segment_id}) that was already used in segment {used_audio_segments[segment_id]+1}")
        else:
            used_audio_segments[segment_id] = i
    
    return {
        "has_overlaps": len(warnings) > 0,
        "warnings": warnings,
        "used_segments": used_audio_segments
    }

# Add this function to extract audio from video file to separate audio file
def extract_audio_track(video_path, output_dir=None):
    """
    Extract audio from a video file to a separate audio file
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save the audio file (uses temp dir if None)
        
    Returns:
        str: Path to extracted audio file or None if extraction failed
    """
    try:
        # Create temp directory if not provided
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        # Generate output path for audio file
        video_filename = os.path.basename(video_path)
        video_name = os.path.splitext(video_filename)[0]
        audio_path = os.path.join(output_dir, f"{video_name}.m4a")
        
        print(f"Extracting audio from: {video_path}")
        print(f"Video path for extraction: {os.path.abspath(video_path)}")
        print(f"Audio output path: {audio_path}")
        
        # Use ffmpeg to extract audio
        cmd = [
            "ffmpeg", "-y", "-i", os.path.abspath(video_path),
            "-vn", "-acodec", "aac", "-b:a", "192k", "-f", "mp4",
            audio_path
        ]
        
        print(f"Running ffmpeg command: {' '.join(cmd)}")
        process = subprocess.run(cmd, capture_output=True, text=True)
        
        if process.returncode == 0:
            print(f"Successfully extracted audio to: {audio_path}")
            return audio_path
        else:
            print(f"Error extracting audio: {process.stderr}")
            return None
    except Exception as e:
        print(f"Exception extracting audio: {str(e)}")
        return None

@error_handler
def assemble_video(sequence, target_resolution=(1080, 1920), output_dir=None, progress_callback=None):
    """
    Assemble a final video from A-Roll and B-Roll segments
    
    Args:
        sequence: List of video segments to assemble
        target_resolution: Target resolution (width, height)
        output_dir: Directory to save output video
        progress_callback: Callback function to update progress
        
    Returns:
        dict: Result dictionary with status, message, and output_path if successful
    """
    if not MOVIEPY_AVAILABLE:
        return {"status": "error", "message": "MoviePy is not available. Please install required packages."}
    
    if progress_callback is None:
        def progress_print(progress, message):
            print(f"Progress: {progress}% - {message}")
        progress_callback = progress_print
    
    # Validate sequence
    if not sequence or not isinstance(sequence, list):
        return {"status": "error", "message": "Invalid sequence format"}
    
    # Check for audio overlaps
    overlaps = check_audio_overlaps(sequence)
    if overlaps["has_overlaps"]:
        print("⚠️ Warning: Potential audio overlaps detected:")
        for warning in overlaps["warnings"]:
            print(f"  - {warning}")
    
    # Check all input files
    missing_files = []
    
    for item in sequence:
        if item["type"] == "aroll_full":
            aroll_path = item.get("aroll_path")
            if not aroll_path or not os.path.exists(aroll_path):
                missing_files.append(f"A-Roll file not found: {aroll_path}")
        elif item["type"] == "broll_with_aroll_audio":
            broll_path = item.get("broll_path")
            aroll_path = item.get("aroll_path")
            
            if not broll_path or not os.path.exists(broll_path):
                missing_files.append(f"B-Roll file not found: {broll_path}")
            
            if not aroll_path or not os.path.exists(aroll_path):
                missing_files.append(f"A-Roll file not found: {aroll_path}")
    
    if missing_files:
        return {
            "status": "error",
            "message": "Missing files required for assembly",
            "missing_files": missing_files
        }
    
    try:
        # Generate a timestamp for the output file - defined here so it's available for all code paths
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Extract audio from all A-Roll segments first
        audio_temp_dir = tempfile.mkdtemp()
        extracted_audio_paths = {}
        
        progress_callback(10, "Extracting audio from A-Roll segments")
        
        # Process all A-Roll segments to extract audio first
        for i, item in enumerate(sequence):
            segment_id = item.get("segment_id", f"segment_{i}")
            if "aroll_path" in item:
                audio_path = extract_audio_track(item["aroll_path"], audio_temp_dir)
                if audio_path:
                    extracted_audio_paths[segment_id] = audio_path
        
        # Load and assemble video clips
        progress_callback(20, "Loading video segments")
        clips = []
        
        for i, item in enumerate(sequence):
            progress_callback(20 + (i / len(sequence) * 40), f"Processing segment {i+1}/{len(sequence)}")
            
            if item["type"] == "aroll_full":
                # Load A-Roll video
                aroll_path = item["aroll_path"]
                segment_id = item.get("segment_id", f"segment_{i}")
                
                try:
                    print(f"Loading A-Roll video: {aroll_path}")
                    clip = mp.VideoFileClip(aroll_path)
                    
                    # Check if clip has valid audio, if not, try to use extracted audio
                    if not has_valid_audio(clip) and segment_id in extracted_audio_paths:
                        audio_path = extracted_audio_paths[segment_id]
                        try:
                            print(f"Loading extracted A-Roll audio: {audio_path}")
                            audio_clip = mp.AudioFileClip(audio_path)
                            
                            # If audio is shorter than video, extend it
                            if audio_clip.duration < clip.duration:
                                print(f"Audio duration {audio_clip.duration} is shorter than video {clip.duration}, extending audio")
                                padding = clip.duration - audio_clip.duration
                                # Create silence to pad the audio
                                # silence = mp.AudioClip(lambda t: 0, duration=padding)
                                # audio_clip = mp.concatenate_audioclips([audio_clip, silence])
                            
                            # Apply audio to clip
                            clip = clip.set_audio(audio_clip)
                            print("Successfully applied extracted audio to A-Roll clip")
                        except Exception as e:
                            print(f"Error applying extracted audio: {str(e)}")
                    elif not has_valid_audio(clip):
                        print(f"Warning: Clip {i+1} has no valid audio, replacing with silent audio")
                        # Create silent audio for the full duration
                        silent_audio = mp.AudioClip(lambda t: 0, duration=clip.duration)
                        clip = clip.set_audio(silent_audio)
                    
                    # Resize to target resolution
                    clip = resize_video(clip, target_resolution)
                    clips.append(clip)
                except Exception as e:
                    print(f"Error loading A-Roll clip: {str(e)}")
                    return {"status": "error", "message": f"Error loading A-Roll clip: {str(e)}"}
            
            elif item["type"] == "broll_with_aroll_audio":
                # Load B-Roll video with A-Roll audio
                broll_path = item["broll_path"]
                aroll_path = item["aroll_path"]
                segment_id = item.get("segment_id", f"segment_{i}")
                
                try:
                    # Load B-Roll video
                    print(f"Loading B-Roll video: {broll_path}")
                    broll_clip = mp.VideoFileClip(broll_path)
                    
                    # Load A-Roll audio if available in extracted paths
                    if segment_id in extracted_audio_paths:
                        audio_path = extracted_audio_paths[segment_id]
                        try:
                            print(f"Successfully loaded extracted A-Roll audio: {audio_path} (duration: {mp.AudioFileClip(audio_path).duration}s)")
                            aroll_audio = mp.AudioFileClip(audio_path)
                            
                            # Apply A-Roll audio to B-Roll video
                            broll_clip = broll_clip.set_audio(aroll_audio)
                            
                            # If B-Roll is shorter than A-Roll audio, loop it
                            if broll_clip.duration < aroll_audio.duration:
                                # Calculate how many times to loop
                                loops = int(aroll_audio.duration / broll_clip.duration) + 1
                                # Create a list of the clip repeated
                                loop_clips = [broll_clip] * loops
                                # Concatenate clips
                                broll_clip = mp.concatenate_videoclips(loop_clips)
                                # Trim to match audio duration
                                broll_clip = broll_clip.subclip(0, aroll_audio.duration)
                            # If B-Roll is longer than A-Roll audio, trim it
                            elif broll_clip.duration > aroll_audio.duration:
                                broll_clip = broll_clip.subclip(0, aroll_audio.duration)
                        except Exception as e:
                            print(f"Error applying A-Roll audio to B-Roll: {str(e)}")
                            # Fallback: Try loading A-Roll directly to extract audio
                            try:
                                print(f"Fallback: Loading A-Roll directly: {aroll_path}")
                                aroll_clip = mp.VideoFileClip(aroll_path)
                                if has_valid_audio(aroll_clip):
                                    broll_clip = broll_clip.set_audio(aroll_clip.audio)
                                    if broll_clip.duration > aroll_clip.duration:
                                        broll_clip = broll_clip.subclip(0, aroll_clip.duration)
                                else:
                                    print(f"Fallback failed: A-Roll has no valid audio")
                                    # Create silent audio
                                    silent_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                                    broll_clip = broll_clip.set_audio(silent_audio)
                                # Close the clip to free resources
                                aroll_clip.close()
                            except Exception as e2:
                                print(f"Fallback failed: {str(e2)}")
                                print(f"Warning: Clip {i+1} has no valid audio, replacing with silent audio")
                                # Create silent audio
                                silent_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                                broll_clip = broll_clip.set_audio(silent_audio)
                    else:
                        print(f"No extracted audio found for segment {segment_id}, trying direct audio extraction")
                        # Fallback: Try loading A-Roll directly to extract audio
                        try:
                            aroll_clip = mp.VideoFileClip(aroll_path)
                            if has_valid_audio(aroll_clip):
                                broll_clip = broll_clip.set_audio(aroll_clip.audio)
                                if broll_clip.duration > aroll_clip.duration:
                                    broll_clip = broll_clip.subclip(0, aroll_clip.duration)
                            else:
                                print(f"A-Roll has no valid audio")
                                # Create silent audio
                                silent_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                                broll_clip = broll_clip.set_audio(silent_audio)
                            # Close the clip to free resources
                            aroll_clip.close()
                        except Exception as e:
                            print(f"Error extracting audio from A-Roll: {str(e)}")
                            print(f"Warning: Clip {i+1} has no valid audio, replacing with silent audio")
                            # Create silent audio
                            silent_audio = mp.AudioClip(lambda t: 0, duration=broll_clip.duration)
                            broll_clip = broll_clip.set_audio(silent_audio)
                    
                    # Resize to target resolution
                    broll_clip = resize_video(broll_clip, target_resolution)
                    clips.append(broll_clip)
                except Exception as e:
                    print(f"Error processing B-Roll with A-Roll audio: {str(e)}")
                    return {"status": "error", "message": f"Error processing B-Roll with A-Roll audio: {str(e)}"}
        
        if not clips:
            return {"status": "error", "message": "No valid clips to assemble"}
        
        # Concatenate clips
        progress_callback(60, "Concatenating video segments")
        final_clip = mp.concatenate_videoclips(clips)
        
        # Set output path
        if output_dir is None:
            output_dir = os.path.join(os.getcwd(), "output")
            os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, f"assembled_video_{timestamp}.mp4")
        
        # Write final video
        progress_callback(80, "Writing final video")
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            fps=30
        )
        
        # Clean up
        progress_callback(95, "Cleaning up")
        for clip in clips:
            clip.close()
        final_clip.close()
        
        # Clean up extracted audio files
        try:
            shutil.rmtree(audio_temp_dir)
        except Exception as e:
            print(f"Warning: Failed to clean up temporary audio files: {str(e)}")
        
        progress_callback(100, "Video assembly complete")
        
        return {
            "status": "success",
            "message": "Video assembled successfully",
            "output_path": output_path
        }
    except Exception as e:
        print(f"Error in video assembly: {str(e)}")
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": str(e),
            "traceback": traceback.format_exc()
        }
    finally:
        # Ensure temp directories are cleaned up
        try:
            if 'audio_temp_dir' in locals():
                shutil.rmtree(audio_temp_dir)
        except Exception:
            pass

if __name__ == "__main__":
    # Simple test if this script is run directly
    if not MOVIEPY_AVAILABLE:
        print("MoviePy is not available. Please run check_dependencies.py first.")
        sys.exit(1)
        
    # Check for arguments
    if len(sys.argv) > 1:
        # Check if first argument is a JSON file with sequence info
        sequence_file = sys.argv[1]
        if os.path.exists(sequence_file):
            try:
                with open(sequence_file, 'r') as f:
                    sequence = json.load(f)
                    
                def progress_print(progress, message):
                    print(f"Progress: {progress}% - {message}")
                    
                result = assemble_video(
                    sequence, 
                    target_resolution=(1080, 1920), 
                    progress_callback=progress_print
                )
                
                if result["status"] == "success":
                    print(f"Video assembly completed successfully!")
                    print(f"Output: {result['output_path']}")
                else:
                    print(f"Error during video assembly: {result['message']}")
            except Exception as e:
                print(f"Error processing sequence file: {str(e)}")
        else:
            print(f"Sequence file not found: {sequence_file}")
    else:
        print("Usage: python video_assembly_helper.py [sequence_file.json]")
        print("To use this script directly, provide a JSON file with sequence information.") 