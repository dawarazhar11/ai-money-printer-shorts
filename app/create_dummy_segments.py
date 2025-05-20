#!/usr/bin/env python3
import os
import subprocess
import argparse
from pathlib import Path

# Specific segment IDs from the project
SEGMENT_IDS = [
    "5169ef5a328149a8b13c365ee7060106",  # SEG1
    "aed87db0234e4965825c7ee4c1067467",  # SEG2
    "e7d47355c21e4190bad8752c799343ee",  # SEG3
    "36064085e2a240768a8368bc6a911aea"   # SEG4
]

def create_dummy_video(output_path, duration=5, resolution="1080x1920", background_color="black", text=None, segment_id=None):
    """
    Create a dummy video file using ffmpeg
    
    Args:
        output_path: Path to save the output video
        duration: Duration in seconds
        resolution: Video resolution (WxH)
        background_color: Background color
        text: Text to display on the video
        segment_id: Segment ID to display
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create the parent directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Base ffmpeg command for creating a colored background
        command = [
            "ffmpeg", "-y",  # Overwrite output files without asking
            "-f", "lavfi",  # Use lavfi input format
            "-i", f"color={background_color}:s={resolution}:d={duration}:r=30",  # Create a colored background
        ]
        
        # Add text overlay if provided
        if text or segment_id:
            display_text = text or f"Segment ID: {segment_id}"
            segment_num = ""
            
            # Extract segment number based on ID
            if segment_id:
                for i, sid in enumerate(SEGMENT_IDS):
                    if sid == segment_id:
                        segment_num = f"SEG{i+1}"
                        break
            
            if segment_num:
                display_text = f"{display_text}\n{segment_num}"
            
            # Add drawtext filter for the main text
            command.extend([
                "-vf", f"drawtext=text='{display_text}':fontcolor=white:fontsize=60:x=(w-text_w)/2:y=(h-text_h)/2"
            ])
        
        # Output settings
        command.extend([
            "-c:v", "libx264",  # Video codec
            "-preset", "ultrafast",  # Encoding speed (fast but larger file)
            "-pix_fmt", "yuv420p",  # Pixel format for compatibility
            output_path  # Output file path
        ])
        
        # Run the ffmpeg command
        print(f"Creating dummy video: {output_path}...")
        result = subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Check if the file was created
        if os.path.exists(output_path):
            print(f"✅ Successfully created dummy video: {output_path}")
            return True
        else:
            print(f"❌ Failed to create dummy video: {output_path}")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Error running ffmpeg: {e}")
        print(f"Error output: {e.stderr.decode()}")
        return False
    except Exception as e:
        print(f"❌ Error creating dummy video: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Create dummy video segments for testing")
    parser.add_argument("--output_dir", help="Output directory", default="media/a-roll")
    parser.add_argument("--duration", help="Video duration in seconds", type=int, default=5)
    parser.add_argument("--resolution", help="Video resolution (WxH)", default="1080x1920")
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    success_count = 0
    
    # Create a dummy video for each segment ID
    for i, segment_id in enumerate(SEGMENT_IDS):
        output_path = output_dir / f"heygen_{segment_id}.mp4"
        
        # Skip if the file already exists
        if output_path.exists():
            print(f"⚠️ File already exists: {output_path}")
            success_count += 1
            continue
        
        # Create the dummy video
        if create_dummy_video(
            str(output_path),
            duration=args.duration,
            resolution=args.resolution,
            segment_id=segment_id,
            text=f"Segment {i+1}"
        ):
            success_count += 1
    
    # Print summary
    print(f"\nCreated {success_count}/{len(SEGMENT_IDS)} dummy videos in {args.output_dir}")
    return 0 if success_count == len(SEGMENT_IDS) else 1

if __name__ == "__main__":
    exit(main()) 