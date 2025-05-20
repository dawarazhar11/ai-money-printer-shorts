#!/usr/bin/env python3
"""
Simple video assembly utility for AI Money Printer Shorts
This is a simpler version of the video assembly using ffmpeg directly
which can be more reliable for some video formats
"""

import os
import sys
import subprocess
import json
import tempfile
from pathlib import Path
from datetime import datetime
import shutil

def check_ffmpeg():
    """Check if ffmpeg is available on the system"""
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

def get_video_info(video_path):
    """Get video information using ffprobe"""
    try:
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,codec_name",
            "-of", "json",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        info = json.loads(result.stdout)
        
        # Extract relevant information
        stream = info.get("streams", [{}])[0]
        return {
            "width": int(stream.get("width", 0)),
            "height": int(stream.get("height", 0)),
            "duration": float(stream.get("duration", 0)),
            "codec": stream.get("codec_name", "unknown")
        }
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error getting video info: {str(e)}")
        return None

def create_concat_file(video_files, concat_file_path):
    """Create an ffmpeg concat file"""
    with open(concat_file_path, 'w') as f:
        for video in video_files:
            # Escape special characters in path
            escaped_path = video.replace("\\", "\\\\").replace("'", "\\'")
            f.write(f"file '{escaped_path}'\n")

def simple_assemble_video(sequence, output_path=None, target_resolution=(1080, 1920), progress_callback=None):
    """
    Assemble videos using ffmpeg concat protocol
    
    Args:
        sequence: List of video segments to assemble (with 'type' and path fields)
        output_path: Path to save the output video
        target_resolution: Target resolution
        progress_callback: Callback function for progress updates
        
    Returns:
        dict: Result with status and output path
    """
    if not check_ffmpeg():
        return {
            "status": "error",
            "message": "FFmpeg is not available. Please install FFmpeg to continue."
        }
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    temp_videos = []
    concat_file = os.path.join(temp_dir, "concat.txt")
    
    # Default output path if none provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        app_dir = Path(__file__).parent.parent.parent.absolute()
        output_dir = app_dir / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(output_dir / f"simple_assembled_video_{timestamp}.mp4")
    
    # Track used audio to prevent overlaps
    used_audio_segments = set()
    
    try:
        if progress_callback:
            progress_callback(10, "Processing video segments...")
        
        # Process all clips sequentially
        for i, item in enumerate(sequence):
            if progress_callback:
                progress_callback(10 + (i / len(sequence) * 50), f"Processing segment {i+1}/{len(sequence)}")
            
            # Skip if this segment's audio was already used (avoids audio overlap)
            segment_id = item.get("segment_id", f"segment_{i}")
            if segment_id in used_audio_segments:
                print(f"⚠️ Skipping segment with duplicate audio: {segment_id}")
                continue
            
            # Mark this audio as used
            used_audio_segments.add(segment_id)
            
            if item["type"] == "aroll_full":
                aroll_path = item.get("aroll_path")
                temp_output = os.path.join(temp_dir, f"segment_{i}.mp4")
                
                # Scale A-Roll to target resolution
                cmd = [
                    "ffmpeg", "-y", "-i", aroll_path,
                    "-vf", f"scale={target_resolution[0]}:{target_resolution[1]}:force_original_aspect_ratio=decrease,pad={target_resolution[0]}:{target_resolution[1]}:(ow-iw)/2:(oh-ih)/2",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k",
                    temp_output
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                temp_videos.append(temp_output)
            
            elif item["type"] == "broll_with_aroll_audio":
                broll_path = item.get("broll_path")
                aroll_path = item.get("aroll_path")
                temp_output = os.path.join(temp_dir, f"segment_{i}.mp4")
                
                # Extract audio from A-Roll
                temp_audio = os.path.join(temp_dir, f"audio_{i}.aac")
                cmd_audio = [
                    "ffmpeg", "-y", "-i", aroll_path,
                    "-vn", "-c:a", "aac", "-b:a", "128k",
                    temp_audio
                ]
                
                subprocess.run(cmd_audio, check=True, capture_output=True)
                
                # Get audio duration using ffprobe
                audio_duration_cmd = [
                    "ffprobe", "-v", "error", "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1", temp_audio
                ]
                audio_duration_result = subprocess.run(audio_duration_cmd, capture_output=True, text=True, check=True)
                audio_duration = float(audio_duration_result.stdout.strip())
                
                # Scale B-Roll and add A-Roll audio with precise timing
                cmd = [
                    "ffmpeg", "-y", "-i", broll_path, "-i", temp_audio,
                    "-vf", f"scale={target_resolution[0]}:{target_resolution[1]}:force_original_aspect_ratio=decrease,pad={target_resolution[0]}:{target_resolution[1]}:(ow-iw)/2:(oh-ih)/2",
                    "-c:v", "libx264", "-preset", "medium", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k",
                    "-shortest",  # End when shortest input stream ends
                    "-af", "afade=t=in:st=0:d=0.1,afade=t=out:st=" + str(audio_duration-0.1) + ":d=0.1",  # Add gentle fades to prevent clicks
                    temp_output
                ]
                
                subprocess.run(cmd, check=True, capture_output=True)
                temp_videos.append(temp_output)
        
        # Create concat file
        create_concat_file(temp_videos, concat_file)
        
        if progress_callback:
            progress_callback(80, "Generating final video...")
        
        # Create final video
        cmd_final = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output_path
        ]
        
        subprocess.run(cmd_final, check=True, capture_output=True)
        
        if progress_callback:
            progress_callback(100, "Video assembly complete")
        
        return {
            "status": "success",
            "message": "Video assembled successfully",
            "output_path": output_path
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error assembling video: {str(e)}"
        }
    finally:
        # Clean up
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Warning: Failed to clean up temp files: {str(e)}")

if __name__ == "__main__":
    # Test if this script is run directly
    if len(sys.argv) > 1:
        # Check if first argument is a JSON file with sequence info
        sequence_file = sys.argv[1]
        if os.path.exists(sequence_file):
            try:
                with open(sequence_file, 'r') as f:
                    sequence = json.load(f)
                
                def progress_print(progress, message):
                    print(f"Progress: {progress}% - {message}")
                
                result = simple_assemble_video(sequence, progress_callback=progress_print)
                
                if result["status"] == "success":
                    print(f"Simple video assembly completed successfully!")
                    print(f"Output: {result['output_path']}")
                else:
                    print(f"Error during simple video assembly: {result['message']}")
            except Exception as e:
                print(f"Error processing sequence file: {str(e)}")
        else:
            print(f"Sequence file not found: {sequence_file}")
    else:
        print("Usage: python simple_assembly.py [sequence_file.json]")
        print("To use this script directly, provide a JSON file with sequence information.") 