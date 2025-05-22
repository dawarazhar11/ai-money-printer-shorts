#!/usr/bin/env python3
"""
Test script for caption generation
This helps debug issues with the captioning functionality
"""

import os
import sys
import json
from pathlib import Path
import time

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
        transcribe_video,
        CAPTION_STYLES
    )
    print("Successfully imported caption modules")
except ImportError as e:
    print(f"Error importing caption modules: {e}")
    sys.exit(1)

def test_transcription(video_path, engine="auto", model_size="base"):
    """Test the transcription functionality"""
    print(f"\n===== TESTING TRANSCRIPTION =====")
    print(f"Video: {video_path}")
    print(f"Engine: {engine}")
    print(f"Model size: {model_size}")
    
    # Run transcription
    result = transcribe_video(video_path, model_size=model_size, engine=engine)
    
    # Print result status
    if result["status"] == "success":
        print(f"✅ Transcription successful")
        print(f"Found {len(result['words'])} words")
        
        # Print first few words with timing
        print("\nSample of transcribed words:")
        for i, word in enumerate(result["words"][:10]):
            print(f"{i+1}. '{word['word']}' ({word['start']:.2f}s - {word['end']:.2f}s)")
        
        # Save transcription to file for inspection
        output_file = f"transcription_test_output.json"
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nTranscription saved to {output_file}")
        
        return result
    else:
        print(f"❌ Transcription failed: {result.get('message', 'Unknown error')}")
        return None

def test_captioning(video_path, style_name="tiktok", engine="auto", model_size="base", custom_style=None):
    """Test the caption generation functionality"""
    print(f"\n===== TESTING CAPTION GENERATION =====")
    print(f"Video: {video_path}")
    print(f"Style: {style_name}")
    
    # Check dependencies
    deps = check_dependencies()
    if not deps["all_available"]:
        print(f"❌ Missing dependencies: {', '.join(deps['missing'])}")
        print("Please install required packages first.")
        return None
    
    # Create test output path
    timestamp = int(os.path.getmtime(video_path))
    output_dir = "test_outputs"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"test_captioned_{style_name}_{timestamp}.mp4")
    
    # Enable verbose debug printing
    def debug_callback(progress, message):
        print(f"Progress: {progress}% - {message}")
    
    # Add captions with extra debug logs
    print(f"Generating captioned video with style '{style_name}'...")
    print(f"Output will be saved to: {output_path}")
    
    # Run the captioning with explicit parameters
    result = add_captions_to_video(
        video_path=video_path,
        output_path=output_path,
        style_name=style_name,
        model_size=model_size,
        engine=engine,
        custom_style=custom_style
    )
    
    # Print result
    if result["status"] == "success":
        print(f"✅ Captioning successful")
        print(f"Output saved to: {result['output_path']}")
        return result["output_path"]
    else:
        print(f"❌ Captioning failed: {result.get('message', 'Unknown error')}")
        if "traceback" in result:
            print("\nError details:")
            print(result["traceback"])
        return None

def test_style_render(style_name="tiktok"):
    """Test individual rendering of caption styles"""
    print(f"\n===== TESTING STYLE RENDERING =====")
    print(f"Style: {style_name}")
    
    try:
        from PIL import Image, ImageDraw, ImageFont
        import numpy as np
        from utils.video.captions import make_frame_with_text, get_system_font
    except ImportError as e:
        print(f"❌ Error importing required modules: {e}")
        return
    
    if style_name not in CAPTION_STYLES:
        print(f"❌ Style '{style_name}' not found")
        print(f"Available styles: {', '.join(CAPTION_STYLES.keys())}")
        return
    
    # Get the style
    style = CAPTION_STYLES[style_name]
    
    # Create a test image
    width, height = 1280, 720
    image = np.zeros((height, width, 3), dtype=np.uint8)
    pil_image = Image.fromarray(image)
    
    # Test with sample text
    test_text = "This is a test caption"
    
    # Try rendering
    try:
        result = make_frame_with_text(
            pil_image,
            text=test_text,
            style=style,
            current_time=0.5
        )
        
        # Save the result
        result_path = f"test_style_{style_name}.png"
        if isinstance(result, np.ndarray):
            Image.fromarray(result).save(result_path)
        elif isinstance(result, Image.Image):
            result.save(result_path)
        else:
            print(f"❌ Unexpected result type: {type(result)}")
            return
            
        print(f"✅ Style test image saved to {result_path}")
    except Exception as e:
        print(f"❌ Error rendering style: {e}")
        import traceback
        print(traceback.format_exc())

def test_all_styles(video_path, engine="auto", model_size="base"):
    """Test all caption styles and effects to diagnose issues"""
    print(f"\n===== TESTING ALL CAPTION STYLES AND EFFECTS =====")
    print(f"Video: {video_path}")
    
    # Create test output directory
    output_dir = "test_outputs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Test basic styles first
    styles_to_test = ["tiktok", "modern_bold", "minimal", "news", "social"]
    results = []
    
    for style_name in styles_to_test:
        print(f"\n--- Testing style: {style_name} ---")
        timestamp = int(time.time())
        output_path = os.path.join(output_dir, f"test_{style_name}_{timestamp}.mp4")
        
        result = add_captions_to_video(
            video_path=video_path,
            output_path=output_path,
            style_name=style_name,
            model_size=model_size,
            engine=engine
        )
        
        if result["status"] == "success":
            print(f"✅ Style {style_name} successful")
            results.append((style_name, output_path, True))
        else:
            print(f"❌ Style {style_name} failed: {result.get('message', 'Unknown error')}")
            results.append((style_name, None, False))
    
    # Test individual typography effects
    effects_to_test = ["fade", "scale", "color_shift", "wave", "typewriter"]
    
    # Use tiktok style as base and add each effect individually
    base_style = "tiktok"
    for effect in effects_to_test:
        print(f"\n--- Testing effect: {effect} ---")
        timestamp = int(time.time())
        output_path = os.path.join(output_dir, f"test_effect_{effect}_{timestamp}.mp4")
        
        # Create custom style with just this effect
        custom_style = CAPTION_STYLES[base_style].copy()
        custom_style["typography_effects"] = [effect]
        
        result = add_captions_to_video(
            video_path=video_path,
            output_path=output_path,
            style_name=base_style,
            model_size=model_size,
            engine=engine,
            custom_style=custom_style
        )
        
        if result["status"] == "success":
            print(f"✅ Effect {effect} successful")
            results.append((f"effect_{effect}", output_path, True))
        else:
            print(f"❌ Effect {effect} failed: {result.get('message', 'Unknown error')}")
            results.append((f"effect_{effect}", None, False))
    
    # Print summary
    print("\n===== TEST RESULTS SUMMARY =====")
    for name, path, success in results:
        status = "✅ SUCCESS" if success else "❌ FAILED"
        output = path if path else "N/A"
        print(f"{status} - {name}: {output}")
    
    return results

def main():
    # Check for command line arguments
    if len(sys.argv) < 2:
        print("Usage: python test_captions.py <video_path> [style_name] [engine] [model_size] [test_mode]")
        print("Example: python test_captions.py test_video.mp4 tiktok auto base all_styles")
        
        # List available styles
        print("\nAvailable caption styles:")
        for name, details in get_available_caption_styles().items():
            print(f"- {name}")
        
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
    
    # Get arguments
    style_name = sys.argv[2] if len(sys.argv) > 2 else "tiktok"
    engine = sys.argv[3] if len(sys.argv) > 3 else "auto"
    model_size = sys.argv[4] if len(sys.argv) > 4 else "base"
    
    # Special test mode
    test_mode = sys.argv[5] if len(sys.argv) > 5 else "normal"
    
    if test_mode == "all_styles":
        # Run comprehensive test of all styles and effects
        test_all_styles(video_path, engine, model_size)
        return
    
    if test_mode == "quick_test":
        # Just run a simple caption test with the most basic style
        print(f"Running quick caption test on {video_path}")
        output_dir = "test_outputs"
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"quick_test_caption.mp4")
        
        result = add_captions_to_video(
            video_path=video_path,
            output_path=output_path,
            style_name="tiktok",
            model_size="tiny",  # Use tiny model for speed
            engine="auto"
        )
        
        if result["status"] == "success":
            print(f"✅ Quick test successful! Output saved to: {result['output_path']}")
        else:
            print(f"❌ Quick test failed: {result.get('message', 'Unknown error')}")
            if "traceback" in result:
                print("\nError details:")
                print(result["traceback"])
        return
    
    # Run the standard tests
    print(f"Testing caption functionality with video: {video_path}")
    
    # First test: style rendering
    test_style_render(style_name)
    
    # Second test: transcription
    transcript = test_transcription(video_path, engine, model_size)
    
    # Third test: captioning
    if transcript:
        captioned_path = test_captioning(video_path, style_name, engine, model_size)
        if captioned_path:
            print(f"\n🎉 All tests completed successfully!")
            print(f"Captioned video available at: {captioned_path}")
        else:
            print(f"\n⚠️ Captioning test failed")
    else:
        print(f"\n⚠️ Transcription test failed, skipping captioning test")

if __name__ == "__main__":
    main() 