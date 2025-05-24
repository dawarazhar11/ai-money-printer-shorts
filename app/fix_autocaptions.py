#!/usr/bin/env python3
"""
Fix Autocaptions Issues
-----------------------
This script diagnoses and fixes issues with the autocaptions feature.
It checks if your video has detectable speech and ensures the transcription
modules are working correctly.

Usage:
python3 fix_autocaptions.py [video_path]
"""

import os
import sys
from pathlib import Path
import time
import subprocess

# Add the app directory to the path
app_dir = Path("/Users/dawarazhar/Desktop/AI-Money-Printer-Shorts/app")
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
    print(f"Added {app_dir} to path")

# Import required modules
try:
    from utils.audio.transcription import transcribe_with_whisper, transcribe_with_faster_whisper, extract_audio, get_available_engines
    from utils.video.captions import add_captions_to_video
    import moviepy.editor as mp
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Please make sure you're running this script from the project directory.")
    sys.exit(1)

def check_audio_levels(video_path):
    """Check if the video has audible sound"""
    try:
        video = mp.VideoFileClip(video_path)
        if video.audio is None:
            print("❌ No audio track found in the video.")
            video.close()
            return False
        
        # Extract audio to analyze levels
        audio = video.audio
        duration = audio.duration
        
        if duration < 1.0:
            print("❌ Audio is too short (< 1 second).")
            video.close()
            return False
        
        print(f"✅ Video has audio track with duration: {duration:.2f} seconds")
        video.close()
        return True
    except Exception as e:
        print(f"❌ Error checking audio levels: {e}")
        return False

def test_transcription(video_path):
    """Test both Whisper and Faster-Whisper transcription on the video"""
    # Extract audio from video
    print("\n📊 Testing transcription capabilities...")
    audio_path = extract_audio(video_path)
    if not audio_path:
        print("❌ Failed to extract audio from video")
        return False
    
    try:
        engines = get_available_engines()
        print(f"Available engines: {', '.join(engines)}")
        
        success = False
        
        # Try with Whisper
        if "whisper" in engines:
            print("\n📝 Testing Whisper transcription:")
            result = transcribe_with_whisper(audio_path, model_size="base")
            print(f"- Status: {result['status']}")
            if result["status"] == "success":
                text = result.get("text", "")
                words = result.get("words", [])
                print(f"- Transcribed text: {text[:100] + '...' if len(text) > 100 else text}")
                print(f"- Words detected: {len(words)}")
                if words:
                    print(f"- First few words: {', '.join([w['word'] for w in words[:5]])}")
                    success = True
                else:
                    print("- No words detected")
        
        # Try with Faster-Whisper
        if "faster_whisper" in engines:
            print("\n📝 Testing Faster-Whisper transcription:")
            result = transcribe_with_faster_whisper(audio_path, model_size="base")
            print(f"- Status: {result['status']}")
            if result["status"] == "success":
                text = result.get("text", "")
                words = result.get("words", [])
                print(f"- Transcribed text: {text[:100] + '...' if len(text) > 100 else text}")
                print(f"- Words detected: {len(words)}")
                if words:
                    print(f"- First few words: {', '.join([w['word'] for w in words[:5]])}")
                    success = True
                else:
                    print("- No words detected")
        
        # Try with custom whisper options if no words were detected
        if not success and "whisper" in engines:
            print("\n📝 Trying Whisper with different options:")
            import whisper
            model = whisper.load_model("base")
            
            print("- Using more verbose options and smaller segments...")
            result = model.transcribe(
                audio_path,
                word_timestamps=True,
                verbose=True,
                language="en",
                initial_prompt="The following is a transcription of speech.",
                condition_on_previous_text=False,
                temperature=0.0,
                suppress_tokens=[]
            )
            
            if result.get("text", "").strip():
                print(f"- Detected text: {result['text'][:100]}...")
                print(f"- Segments: {len(result.get('segments', []))}")
                
                # Check for words in segments
                word_count = 0
                for segment in result.get("segments", []):
                    if "words" in segment:
                        word_count += len(segment["words"])
                
                print(f"- Words detected: {word_count}")
                if word_count > 0:
                    success = True
        
        return success
    finally:
        # Clean up temp file
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)

def test_generate_captions(video_path):
    """Test generating captions using various styles"""
    print("\n🎬 Testing caption generation...")
    
    timestamp = int(time.time())
    output_path = f"/tmp/test_captioned_{timestamp}.mp4"
    
    result = add_captions_to_video(
        video_path=video_path,
        output_path=output_path,
        style_name="tiktok",
        model_size="base",
        engine="auto"
    )
    
    if result["status"] == "success":
        print(f"✅ Successfully generated captions! Output: {output_path}")
        print(f"🔍 You can check this video to see if the captions appear correctly.")
        return True
    else:
        print(f"❌ Failed to generate captions: {result.get('message', 'Unknown error')}")
        if "traceback" in result:
            print(f"Error traceback: {result['traceback']}")
        return False

def main():
    # Check if video path was provided
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
    else:
        # Look for video files in the media directory
        media_dir = os.path.join(app_dir, "media")
        video_files = []
        
        if os.path.exists(media_dir):
            for root, dirs, files in os.walk(media_dir):
                for file in files:
                    if file.endswith(('.mp4', '.mov', '.avi', '.mkv')):
                        video_files.append(os.path.join(root, file))
        
        if not video_files:
            print("No video files found! Please provide a video path.")
            print(f"Usage: python3 {sys.argv[0]} [video_path]")
            return
        
        # Use the first video file
        video_path = video_files[0]
    
    # Check if file exists
    if not os.path.exists(video_path):
        print(f"Video file not found: {video_path}")
        return
    
    print(f"🔍 Analyzing video: {video_path}")
    
    # Check audio levels
    has_audio = check_audio_levels(video_path)
    
    # Test transcription
    transcription_works = test_transcription(video_path)
    
    # Try to generate captions
    captions_work = test_generate_captions(video_path)
    
    # Show summary
    print("\n📋 Diagnosis Summary:")
    print(f"- Audio in video: {'✅ Yes' if has_audio else '❌ No'}")
    print(f"- Transcription works: {'✅ Yes' if transcription_works else '❌ No'}")
    print(f"- Caption generation works: {'✅ Yes' if captions_work else '❌ No'}")
    
    if not has_audio:
        print("\n🔧 Solution: Your video doesn't have audio. Add audio to your video or use a different video.")
    elif not transcription_works:
        print("\n🔧 Solution: Speech recognition is not detecting any words in your video.")
        print("   Try a video with clearer speech, or manually add a subtitle file.")
    elif not captions_work:
        print("\n🔧 Solution: There's an issue with the caption generation process.")
        print("   Check the error messages above and try using a different caption style.")
    else:
        print("\n✅ Everything seems to be working correctly!")
        print("   If you're still seeing 'No Speech Detected', your video may have very quiet audio")
        print("   or speech that's difficult for the AI to recognize.")

if __name__ == "__main__":
    main() 