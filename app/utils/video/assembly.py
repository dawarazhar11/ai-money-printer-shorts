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

# Add this function to extract audio from video file to separate audio file
def extract_audio_track(video_path, output_dir=None):
    """
    Extract audio from a video file to a separate audio file
    
    Args:
        video_path: Path to video file
        output_dir: Directory to save the audio file (uses temp dir if None)
        
    Returns:
        dict: Result with status and audio file path
    """
    try:
        print(f"Extracting audio from: {video_path}")
        use_temp_dir = output_dir is None
        
        # Convert to absolute path for reliability
        video_path = os.path.abspath(video_path)
        
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            return {
                "status": "error",
                "message": f"Video file not found: {video_path}"
            }
        
        if use_temp_dir:
            # Use a temporary directory if no output_dir provided
            output_dir = tempfile.mkdtemp()
        
        # Ensure the output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output filename
        video_name = os.path.basename(video_path)
        audio_name = os.path.splitext(video_name)[0] + ".m4a"
        audio_path = os.path.join(output_dir, audio_name)
        
        # Extract audio using ffmpeg directly for more reliable extraction
        try:
            print(f"Video path for extraction: {video_path}")
            print(f"Audio output path: {audio_path}")
            
            cmd = [
                "ffmpeg", "-y", 
                "-i", video_path,
                "-vn",  # No video
                "-acodec", "aac",  # AAC audio codec
                "-b:a", "192k",  # Bitrate
                "-f", "mp4",  # Force MP4 format
                audio_path
            ]
            
            print(f"Running ffmpeg command: {' '.join(cmd)}")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                print(f"Successfully extracted audio to: {audio_path}")
                return {
                    "status": "success",
                    "audio_path": audio_path,
                    "is_temp": use_temp_dir,
                    "temp_dir": output_dir if use_temp_dir else None
                }
            else:
                print(f"Audio extraction failed or produced empty file for: {video_path}")
                return {
                    "status": "error",
                    "message": "Audio extraction failed or produced empty file"
                }
                
        except subprocess.SubprocessError as e:
            print(f"FFmpeg error while extracting audio: {str(e)}")
            print(f"FFmpeg stderr: {e.stderr if hasattr(e, 'stderr') else 'N/A'}")
            
            # Fallback to MoviePy for extraction
            if MOVIEPY_AVAILABLE:
                try:
                    print(f"Attempting audio extraction with MoviePy for: {video_path}")
                    video = mp.VideoFileClip(video_path)
                    if video.audio is not None:
                        video.audio.write_audiofile(audio_path)
                        video.close()
                        
                        if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                            print(f"Successfully extracted audio with MoviePy to: {audio_path}")
                            return {
                                "status": "success",
                                "audio_path": audio_path,
                                "is_temp": use_temp_dir,
                                "temp_dir": output_dir if use_temp_dir else None
                            }
                except Exception as mp_err:
                    print(f"MoviePy fallback also failed: {str(mp_err)}")
            
            return {
                "status": "error",
                "message": f"Audio extraction failed: {str(e)}"
            }
                
    except Exception as e:
        print(f"Error in audio extraction: {str(e)}")
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Error in audio extraction: {str(e)}"
        }

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
    
    # Create a temp directory for extracted audio files
    temp_dirs = []
    
    try:
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
        
        # Pre-extract all audio from A-Roll clips for better reliability
        aroll_audio_map = {}  # Maps aroll_path to extracted audio path
        
        for i, item in enumerate(sequence):
            if progress_callback:
                progress_callback(i / len(sequence) * 5, f"Pre-extracting audio for segment {i+1}/{len(sequence)}")
            
            if not isinstance(item, dict):
                return {
                    "status": "error", 
                    "message": f"Invalid segment format at position {i}. Expected a dictionary."
                }
            
            # Extract audio from A-Roll clips
            aroll_path = item.get("aroll_path")
            if aroll_path and aroll_path not in aroll_audio_map:
                # Extract audio to a separate file
                audio_result = extract_audio_track(aroll_path)
                
                if audio_result["status"] == "success":
                    aroll_audio_map[aroll_path] = audio_result["audio_path"]
                    
                    # Keep track of temp dirs to clean up later
                    if audio_result.get("is_temp", False) and audio_result.get("temp_dir"):
                        temp_dirs.append(audio_result["temp_dir"])
                else:
                    print(f"Warning: Failed to extract audio from {aroll_path}: {audio_result.get('message', 'Unknown error')}")
        
        # Now validate and process the sequence
        for i, item in enumerate(sequence):
            if progress_callback:
                progress_callback(5 + (i / len(sequence) * 5), f"Checking files for segment {i+1}/{len(sequence)}")
            
            if item["type"] == "aroll_full":
                # Full A-Roll segment (video + audio)
                aroll_path = item.get("aroll_path")
                aroll_check = check_file(aroll_path, "video")
                
                if aroll_check["status"] == "error":
                    missing_files.append(aroll_check["message"])
                    continue
                    
                # Get the extracted audio path if available
                aroll_audio_path = aroll_audio_map.get(aroll_path)
                
                clips_info.append({
                    "index": i,
                    "type": "aroll_full",
                    "aroll_path": aroll_path,
                    "aroll_audio_path": aroll_audio_path,
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
                
                # Get the extracted audio path if available
                aroll_audio_path = aroll_audio_map.get(aroll_path)
                    
                clips_info.append({
                    "index": i,
                    "type": "broll_with_aroll_audio",
                    "broll_path": broll_path,
                    "aroll_path": aroll_path,
                    "aroll_audio_path": aroll_audio_path,
                    "broll_info": broll_check,
                    "aroll_info": aroll_check
                })
        
        # Check if any files are missing
        if missing_files:
            # Clean up temp dirs
            for temp_dir in temp_dirs:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Error cleaning up temp dir {temp_dir}: {str(e)}")
                    
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
                    
                    # If we have extracted audio, use it
                    if clip_info.get("aroll_audio_path") and os.path.exists(clip_info["aroll_audio_path"]):
                        try:
                            # Load the extracted audio
                            aroll_audio = mp.AudioFileClip(clip_info["aroll_audio_path"])
                            
                            # Use the extracted audio with proper duration matching
                            if aroll_audio.duration > aroll_clip.duration:
                                aroll_audio = aroll_audio.subclip(0, aroll_clip.duration)
                            elif aroll_audio.duration < aroll_clip.duration:
                                # If audio is shorter, extend it by looping or using silent audio
                                print(f"Audio duration {aroll_audio.duration} is shorter than video {aroll_clip.duration}, extending audio")
                                silent_audio = mp.AudioClip(lambda t: [0, 0], duration=aroll_clip.duration - aroll_audio.duration)
                                aroll_audio = mp.concatenate_audioclips([aroll_audio, silent_audio])
                            
                            # Set the audio to the clip
                            aroll_clip = aroll_clip.set_audio(aroll_audio)
                            print(f"Successfully applied extracted audio to A-Roll clip")
                        except Exception as audio_err:
                            print(f"Error applying extracted audio to A-Roll: {str(audio_err)}")
                            # Continue with original audio
                    
                    # Resize to target resolution
                    aroll_clip = resize_video(aroll_clip, target_resolution)
                    processed_clips.append(aroll_clip)
                    
                elif clip_info["type"] == "broll_with_aroll_audio":
                    # Load B-Roll clip
                    broll_path = clip_info["broll_path"]
                    aroll_path = clip_info["aroll_path"]
                    
                    # Check if B-Roll is an image (by extension)
                    is_image = broll_path.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                    
                    # If we have extracted A-Roll audio, use it directly
                    if clip_info.get("aroll_audio_path") and os.path.exists(clip_info["aroll_audio_path"]):
                        try:
                            # Load the extracted audio
                            aroll_audio = mp.AudioFileClip(clip_info["aroll_audio_path"])
                            aroll_duration = aroll_audio.duration
                            print(f"Successfully loaded extracted A-Roll audio: {clip_info['aroll_audio_path']} (duration: {aroll_duration}s)")
                        except Exception as audio_err:
                            print(f"Error loading extracted audio: {str(audio_err)}")
                            
                            # Fallback: Load A-Roll to get duration and try to extract audio directly
                            aroll_clip = mp.VideoFileClip(aroll_path)
                            aroll_duration = aroll_clip.duration
                            
                            # Try to get audio from A-Roll clip
                            if has_valid_audio(aroll_clip):
                                aroll_audio = aroll_clip.audio
                                print(f"Using direct audio from A-Roll clip")
                            else:
                                # Create silent audio as last resort
                                print(f"Creating silent audio for A-Roll clip")
                                aroll_audio = mp.AudioClip(lambda t: [0, 0], duration=aroll_duration)
                            
                            # Close A-Roll clip
                            aroll_clip.close()
                        except Exception as e:
                            print(f"Error during audio processing: {str(e)}")
                            # Create silent audio as fallback
                            aroll_audio = mp.AudioClip(lambda t: [0, 0], duration=aroll_duration)
                            print(f"Using silent audio fallback for A-Roll clip {aroll_path}")
                        
                        # Close A-Roll clip
                        aroll_clip.close()
                    
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
                    
            except Exception as e:
                # Clean up processed clips
                for clip in processed_clips:
                    try:
                        clip.close()
                    except:
                        pass
                
                # Clean up temp dirs
                for temp_dir in temp_dirs:
                    try:
                        shutil.rmtree(temp_dir)
                    except Exception as temp_err:
                        print(f"Error cleaning up temp dir {temp_dir}: {str(temp_err)}")
                        
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
            # Clean up temp dirs
            for temp_dir in temp_dirs:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Error cleaning up temp dir {temp_dir}: {str(e)}")
                    
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
            
            # Clean up temp dirs
            for temp_dir in temp_dirs:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    print(f"Error cleaning up temp dir {temp_dir}: {str(e)}")
            
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
            
            # Clean up temp dirs
            for temp_dir in temp_dirs:
                try:
                    shutil.rmtree(temp_dir)
                except Exception as temp_err:
                    print(f"Error cleaning up temp dir {temp_dir}: {str(temp_err)}")
            
            return {
                "status": "error",
                "message": f"Error during final video assembly: {str(e)}",
                "traceback": traceback.format_exc()
            }
    except Exception as e:
        # Clean up temp dirs
        for temp_dir in temp_dirs:
            try:
                shutil.rmtree(temp_dir)
            except Exception as temp_err:
                print(f"Error cleaning up temp dir {temp_dir}: {str(temp_err)}")
                
        return {
            "status": "error",
            "message": f"Unexpected error during video assembly: {str(e)}",
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