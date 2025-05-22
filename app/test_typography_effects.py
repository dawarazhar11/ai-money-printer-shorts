#!/usr/bin/env python3
"""
Test script for typography effects in caption generation
This helps debug individual typography effects
"""

import os
import sys
import json
import time
from pathlib import Path

# Add the parent directory to sys.path
app_dir = Path(__file__).parent.absolute()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
    print(f"Added {app_dir} to path")

try:
    from utils.video.captions import (
        add_captions_to_video,
        get_available_caption_styles,
        CAPTION_STYLES,
        TYPOGRAPHY_EFFECTS
    )
    print("Successfully imported caption modules")
except ImportError as e:
    print(f"Error importing caption modules: {e}")
    sys.exit(1)

def test_single_effect(video_path, effect_name, base_style="tiktok", engine="auto", model_size="tiny"):
    """Test a single typography effect"""
    print(f"\n===== TESTING TYPOGRAPHY EFFECT: {effect_name} =====")
    
    if effect_name not in TYPOGRAPHY_EFFECTS:
        print(f"Effect '{effect_name}' not found!")
        print(f"Available effects: {', '.join(TYPOGRAPHY_EFFECTS.keys())}")
        return None
    
    # Create a custom style with just this effect
    custom_style = CAPTION_STYLES[base_style].copy()
    custom_style["typography_effects"] = [effect_name]
    
    # Create output filename
    timestamp = int(time.time())
    output_dir = "typography_test_outputs"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"effect_{effect_name}_{timestamp}.mp4")
    
    print(f"Testing effect '{effect_name}' with parameters:")
    for param, value in TYPOGRAPHY_EFFECTS[effect_name]["params"].items():
        print(f"  - {param}: {value}")
    
    # Run the captioning with this effect
    result = add_captions_to_video(
        video_path=video_path,
        output_path=output_path,
        style_name=base_style,
        model_size=model_size,
        engine=engine,
        custom_style=custom_style
    )
    
    # Check result
    if result["status"] == "success":
        print(f"✅ Effect '{effect_name}' successfully applied!")
        print(f"Output saved to: {result['output_path']}")
        return result["output_path"]
    else:
        print(f"❌ Failed to apply effect '{effect_name}': {result.get('message', 'Unknown error')}")
        if "traceback" in result:
            print(f"Error details:\n{result['traceback']}")
        return None

def test_combined_effects(video_path, effect_names, base_style="tiktok", engine="auto", model_size="tiny"):
    """Test multiple typography effects combined"""
    print(f"\n===== TESTING COMBINED EFFECTS: {', '.join(effect_names)} =====")
    
    # Validate all effects exist
    for effect in effect_names:
        if effect not in TYPOGRAPHY_EFFECTS:
            print(f"Effect '{effect}' not found!")
            print(f"Available effects: {', '.join(TYPOGRAPHY_EFFECTS.keys())}")
            return None
    
    # Create a custom style with these effects
    custom_style = CAPTION_STYLES[base_style].copy()
    custom_style["typography_effects"] = effect_names
    
    # Create output filename
    timestamp = int(time.time())
    effects_str = "_".join(effect_names)
    output_dir = "typography_test_outputs"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"combined_{effects_str}_{timestamp}.mp4")
    
    print(f"Testing combined effects: {', '.join(effect_names)}")
    
    # Run the captioning with these effects
    result = add_captions_to_video(
        video_path=video_path,
        output_path=output_path,
        style_name=base_style,
        model_size=model_size,
        engine=engine,
        custom_style=custom_style
    )
    
    # Check result
    if result["status"] == "success":
        print(f"✅ Combined effects successfully applied!")
        print(f"Output saved to: {result['output_path']}")
        return result["output_path"]
    else:
        print(f"❌ Failed to apply combined effects: {result.get('message', 'Unknown error')}")
        if "traceback" in result:
            print(f"Error details:\n{result['traceback']}")
        return None

def main():
    # Check for command line arguments
    if len(sys.argv) < 2:
        print("Usage: python test_typography_effects.py <video_path> [effect_name|'all'|'combined']")
        print("Examples:")
        print("  python test_typography_effects.py video.mp4 fade")
        print("  python test_typography_effects.py video.mp4 all")
        print("  python test_typography_effects.py video.mp4 combined")
        
        # List available effects
        print("\nAvailable typography effects:")
        for name, details in TYPOGRAPHY_EFFECTS.items():
            print(f"- {name}: {details['description']}")
        
        # Check if we have any mp4 files in the current directory
        mp4_files = list(Path(".").glob("**/*.mp4"))
        if mp4_files:
            print("\nFound video files:")
            for i, f in enumerate(mp4_files[:5]):
                print(f"{i+1}. {f}")
            
            # Propose using the first mp4 file
            selected_file = mp4_files[0]
            print(f"\nUsing first found video: {selected_file}")
            video_path = str(selected_file)
        else:
            print("\nNo video files found in current directory. Please specify a video path.")
            sys.exit(1)
    else:
        video_path = sys.argv[1]
    
    # Check if the video exists
    if not os.path.exists(video_path):
        print(f"Error: Video file not found: {video_path}")
        sys.exit(1)
    
    # Determine what to test
    if len(sys.argv) > 2:
        effect_arg = sys.argv[2]
    else:
        effect_arg = "all"
    
    # Test based on the argument
    if effect_arg == "all":
        # Test all effects one by one
        results = []
        for effect_name in TYPOGRAPHY_EFFECTS.keys():
            output_path = test_single_effect(video_path, effect_name)
            results.append((effect_name, output_path))
        
        # Print summary
        print("\n===== TEST RESULTS SUMMARY =====")
        for name, path in results:
            status = "✅ SUCCESS" if path else "❌ FAILED"
            output = path if path else "N/A"
            print(f"{status} - {name}: {output}")
            
    elif effect_arg == "combined":
        # Test a combination of effects
        combined_effects = ["fade", "scale", "color_shift"]
        test_combined_effects(video_path, combined_effects)
        
    else:
        # Test a single effect
        test_single_effect(video_path, effect_arg)

if __name__ == "__main__":
    main() 