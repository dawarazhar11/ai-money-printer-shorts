#!/usr/bin/env python3
import os
import sys
import traceback
from pathlib import Path
import time
from datetime import datetime
import json

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
            return False
        # Try to access a frame to check if audio is valid
        _ = clip.audio.get_frame(0)
        return True
    except (AttributeError, IOError, ValueError) as e:
        print(f"Audio validation error: {str(e)}")
        return False

@error_handler
def assemble_video(sequence, target_resolution=(1080, 1920), output_dir=None, progress_callback=None):
    """
    Assemble video clips according to the sequence
    
    Args:
        sequence: List of video segments to assemble
        target_resolution: Target resolution (width, height)
        output_dir: Directory to save the output video
        progress_callback: Optional function to report progress
        
    Returns:
        dict: Result containing status and output path
    """
    # Check if MoviePy is available first
    if not MOVIEPY_AVAILABLE:
        return {
            "status": "error", 
            "message": "MoviePy is not available. Please run check_dependencies.py"
        }
    
    # Default output directory
    if output_dir is None:
        output_dir = Path(app_root) / "output"
    else:
        output_dir = Path(output_dir)
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate output filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = str(output_dir / f"assembled_video_{timestamp}.mp4")
    
    # Report progress
    if progress_callback:
        progress_callback(0, "Validating input files")
    
    # Validate sequence
    if not sequence or not isinstance(sequence, list):
        return {
            "status": "error", 
            "message": "Invalid sequence format. Expected a list of video segments."
        }
    
    # Validate each segment and check files
    clips_info = []
    missing_files = []
    
    for i, item in enumerate(sequence):
        if progress_callback:
            progress_callback(i / len(sequence) * 10, f"Checking files for segment {i+1}/{len(sequence)}")
        
        if not isinstance(item, dict):
            return {
                "status": "error", 
                "message": f"Invalid segment format at position {i}. Expected a dictionary."
            }
        
        if item["type"] == "aroll_full":
            # Full A-Roll segment (video + audio)
            aroll_path = item.get("aroll_path")
            aroll_check = check_file(aroll_path, "video")
            
            if aroll_check["status"] == "error":
                missing_files.append(aroll_check["message"])
                continue
                
            clips_info.append({
                "index": i,
                "type": "aroll_full",
                "aroll_path": aroll_path,
                "aroll_info": aroll_check
            })
            
        elif item["type"] == "broll_with_aroll_audio":
            # B-Roll video with A-Roll audio
            broll_path = item.get("broll_path")
            aroll_path = item.get("aroll_path")
            
            broll_check = check_file(broll_path, "video")
            aroll_check = check_file(aroll_path, "video")
            
            if broll_check["status"] == "error":
                missing_files.append(broll_check["message"])
            
            if aroll_check["status"] == "error":
                missing_files.append(aroll_check["message"])
                
            if broll_check["status"] == "error" or aroll_check["status"] == "error":
                continue
                
            clips_info.append({
                "index": i,
                "type": "broll_with_aroll_audio",
                "broll_path": broll_path,
                "aroll_path": aroll_path,
                "broll_info": broll_check,
                "aroll_info": aroll_check
            })
    
    # Check if any files are missing
    if missing_files:
        return {
            "status": "error",
            "message": "Missing files required for video assembly",
            "missing_files": missing_files
        }
    
    # Report progress
    if progress_callback:
        progress_callback(10, "Processing video clips")
    
    # Process clips
    processed_clips = []
    for i, clip_info in enumerate(clips_info):
        try:
            if progress_callback:
                progress_callback(10 + (i / len(clips_info) * 40), f"Processing clip {i+1}/{len(clips_info)}")
            
            if clip_info["type"] == "aroll_full":
                # Load A-Roll clip
                aroll_clip = mp.VideoFileClip(clip_info["aroll_path"])
                
                # Resize to target resolution
                aroll_clip = resize_video(aroll_clip, target_resolution)
                processed_clips.append(aroll_clip)
                
            elif clip_info["type"] == "broll_with_aroll_audio":
                # Load B-Roll clip
                broll_path = clip_info["broll_path"]
                aroll_path = clip_info["aroll_path"]
                
                # Check if B-Roll is an image (by extension)
                is_image = broll_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                
                # Load A-Roll to get audio and duration
                aroll_clip = mp.VideoFileClip(aroll_path)
                aroll_duration = aroll_clip.duration
                
                # Verify that A-Roll has valid audio
                if not has_valid_audio(aroll_clip):
                    print(f"Warning: A-Roll clip {aroll_path} has no valid audio, using silent audio")
                    # Create silent audio for the duration of the A-Roll clip
                    aroll_audio = mp.AudioClip(lambda t: [0, 0], duration=aroll_duration)
                else:
                    aroll_audio = aroll_clip.audio
                
                if is_image:
                    # Create video from image with A-Roll duration
                    broll_clip = mp.ImageClip(broll_path, duration=aroll_duration)
                else:
                    # Load B-Roll video
                    broll_clip = mp.VideoFileClip(broll_path)
                    
                    # Handle duration mismatch
                    if broll_clip.duration < aroll_duration:
                        # Loop B-Roll if it's shorter
                        broll_clip = broll_clip.loop(duration=aroll_duration)
                    elif broll_clip.duration > aroll_duration:
                        # Trim B-Roll if it's longer
                        broll_clip = broll_clip.subclip(0, aroll_duration)
                
                # Resize B-Roll to target resolution
                broll_clip = resize_video(broll_clip, target_resolution)
                
                # Add A-Roll audio to B-Roll
                broll_clip = broll_clip.set_audio(aroll_audio)
                processed_clips.append(broll_clip)
                
                # Close A-Roll clip
                aroll_clip.close()
                
        except Exception as e:
            # Clean up processed clips
            for clip in processed_clips:
                try:
                    clip.close()
                except:
                    pass
                    
            return {
                "status": "error",
                "message": f"Error processing clip {i+1}: {str(e)}",
                "traceback": traceback.format_exc()
            }
    
    # Report progress
    if progress_callback:
        progress_callback(50, "Concatenating clips")
    
    # Concatenate clips if we have any
    if not processed_clips:
        return {
            "status": "error",
            "message": "No valid clips were created"
        }
    
    try:
        # Verify all clips have valid audio before concatenating
        for i, clip in enumerate(processed_clips):
            if not has_valid_audio(clip):
                print(f"Warning: Clip {i+1} has no valid audio, replacing with silent audio")
                # Create silent audio for the clip
                clip = clip.set_audio(mp.AudioClip(lambda t: [0, 0], duration=clip.duration))
                processed_clips[i] = clip
        
        # Concatenate all clips
        final_clip = mp.concatenate_videoclips(processed_clips)
        
        # Report progress
        if progress_callback:
            progress_callback(60, "Rendering final video")
        
        # Use simpler params for more compatibility
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            threads=2,  # Reduce threads to avoid memory issues
            fps=30,
            verbose=False,
            ffmpeg_params=["-strict", "-2"]  # Add more compatible params
        )
        
        # Report progress
        if progress_callback:
            progress_callback(100, "Video assembly complete")
        
        # Clean up
        for clip in processed_clips:
            clip.close()
        final_clip.close()
        
        return {
            "status": "success",
            "output_path": output_path,
            "duration": final_clip.duration,
            "resolution": target_resolution
        }
    
    except Exception as e:
        # Clean up
        for clip in processed_clips:
            try:
                clip.close()
            except:
                pass
        
        return {
            "status": "error",
            "message": f"Error during final video assembly: {str(e)}",
            "traceback": traceback.format_exc()
        }

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