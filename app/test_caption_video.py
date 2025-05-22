#!/usr/bin/env python3
"""
Test script for captioning a video to verify the fixes
"""

import os
import sys
import traceback
from pathlib import Path

# Add the parent directory to sys.path
app_dir = Path(__file__).parent.absolute()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
    print(f"Added {app_dir} to path")

try:
    from utils.video.captions import (
        check_dependencies,
        add_captions_to_video, 
        get_available_caption_styles,
        CAPTION_STYLES
    )
    print("Successfully imported caption modules")
except ImportError as e:
    print(f"Error importing caption modules: {e}")
    print(traceback.format_exc())
    sys.exit(1)

def main():
    # Find a sample video file to test with
    sample_video = None
    
    # Look for mp4 files in the current directory
    mp4_files = list(Path(".").glob("**/*.mp4"))
    if mp4_files:
        print(f"Found {len(mp4_files)} video files:")
        for i, file_path in enumerate(mp4_files[:5]):
            print(f"{i+1}. {file_path}")
        
        # Use the first video file
        sample_video = str(mp4_files[0])
        print(f"\nUsing video: {sample_video}")
    else:
        print("No video files found. Please provide a video path as a command line argument.")
        if len(sys.argv) > 1:
            sample_video = sys.argv[1]
            if not os.path.exists(sample_video):
                print(f"Error: Video file not found: {sample_video}")
                sys.exit(1)
            print(f"Using provided video: {sample_video}")
        else:
            print("No video path provided. Exiting.")
            sys.exit(1)
    
    # Check dependencies
    deps = check_dependencies()
    if not deps["all_available"]:
        print(f"❌ Missing dependencies: {', '.join(deps['missing'])}")
        print("Please install required packages first.")
        sys.exit(1)
    
    # Create output directory
    output_dir = "caption_test_output"
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output path
    output_path = os.path.join(output_dir, f"captioned_video_test.mp4")
    
    # Add captions to the video
    print(f"Adding captions to {sample_video}...")
    print(f"Output will be saved to {output_path}")
    
    # Use a simple style for the test
    style_name = "tiktok"
    
    result = add_captions_to_video(
        video_path=sample_video,
        output_path=output_path,
        style_name=style_name,
        model_size="tiny",  # Use tiny model for faster testing
        engine="auto"
    )
    
    # Check result
    if result["status"] == "success":
        print("\n✅ Caption generation successful!")
        print(f"Output saved to: {result['output_path']}")
        print("\nCommands to view the captioned video:")
        print(f"  - macOS: open {result['output_path']}")
        print(f"  - Linux: xdg-open {result['output_path']}")
        print(f"  - Windows: start {result['output_path']}")
    else:
        print("\n❌ Caption generation failed!")
        print(f"Error: {result.get('message', 'Unknown error')}")
        if "traceback" in result:
            print("\nError details:")
            print(result["traceback"])

if __name__ == "__main__":
    main() 