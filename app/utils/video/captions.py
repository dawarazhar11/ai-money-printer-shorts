#!/usr/bin/env python3
"""
Caption generator for AI Money Printer Shorts videos
Provides automatic caption generation and stylish overlay options
"""

import os
import sys
import tempfile
import json
import subprocess
import traceback
from pathlib import Path
from datetime import datetime
import shutil

# Add parent directory to path
app_root = Path(__file__).parent.parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path from captions module")

# Try to import required packages
try:
    import moviepy.editor as mp
    from moviepy.video.tools.subtitles import SubtitlesClip
    import numpy as np
    import whisper
    from PIL import Image, ImageDraw, ImageFont
    DEPENDENCIES_AVAILABLE = True
    print("✅ Successfully imported caption dependencies")
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    print(f"❌ Error importing caption dependencies: {str(e)}")
    print("Please run the dependencies installation to use caption features")

def check_dependencies():
    """Check if all required dependencies are installed"""
    missing = []
    
    try:
        import moviepy.editor as mp
    except ImportError:
        missing.append("moviepy")
    
    try:
        import whisper
    except ImportError:
        missing.append("whisper")
    
    try:
        from PIL import Image
    except ImportError:
        missing.append("pillow")
    
    # Check ffmpeg installation
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode != 0:
            missing.append("ffmpeg")
    except:
        missing.append("ffmpeg")
    
    return {
        "all_available": len(missing) == 0,
        "missing": missing
    }

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

@error_handler
def transcribe_video(video_path, model_size="base"):
    """
    Transcribe video audio to text with timestamps
    
    Args:
        video_path: Path to the video file
        model_size: Whisper model size (tiny, base, small, medium, large)
        
    Returns:
        dict: Results containing transcript with word-level timing
    """
    if not DEPENDENCIES_AVAILABLE:
        return {"status": "error", "message": "Required dependencies not available"}
    
    try:
        print(f"Loading Whisper model: {model_size}")
        model = whisper.load_model(model_size)
        
        # Extract audio from video if needed
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, "audio.wav")
        
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
            audio_path
        ]
        
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Transcribe with word-level timestamps
        print(f"Transcribing audio with Whisper...")
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            verbose=True
        )
        
        shutil.rmtree(temp_dir)
        
        return {
            "status": "success",
            "transcript": result["text"],
            "segments": result["segments"],
            "words": [
                {
                    "word": segment["words"][i]["word"], 
                    "start": segment["words"][i]["start"], 
                    "end": segment["words"][i]["end"]
                }
                for segment in result["segments"]
                for i in range(len(segment["words"]))
            ]
        }
    except Exception as e:
        return {"status": "error", "message": f"Transcription failed: {str(e)}"}

# Caption style presets
CAPTION_STYLES = {
    "tiktok": {
        "font": "Arial-Bold.ttf",
        "font_size": 40,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 180),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True
    },
    "modern_bold": {
        "font": "Impact.ttf",
        "font_size": 45,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (255, 0, 0, 200),  # Semi-transparent red
        "highlight_padding": 12,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True
    },
    "minimal": {
        "font": "Arial.ttf",
        "font_size": 35,
        "text_color": (255, 255, 255),  # White
        "highlight_color": None,  # No background
        "highlight_padding": 0,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": False,
        "word_by_word": False
    },
    "news": {
        "font": "Georgia.ttf",
        "font_size": 38,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 139, 230),  # Dark blue
        "highlight_padding": 10,
        "position": "bottom",
        "align": "center",
        "shadow": False,
        "animate": False,
        "word_by_word": False
    },
    "social": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (50, 50, 50, 200),  # Dark gray
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True
    },
}

def get_system_font(font_name):
    """Get a system font or default to Arial"""
    # Common font locations by platform
    if sys.platform == "darwin":  # macOS
        font_dirs = [
            "/System/Library/Fonts",
            "/Library/Fonts",
            os.path.expanduser("~/Library/Fonts")
        ]
    elif sys.platform == "win32":  # Windows
        font_dirs = [
            "C:\\Windows\\Fonts"
        ]
    else:  # Linux and others
        font_dirs = [
            "/usr/share/fonts",
            "/usr/local/share/fonts",
            os.path.expanduser("~/.fonts")
        ]
    
    # Common font filename patterns by requested name
    font_options = {
        "Arial-Bold.ttf": ["Arial Bold.ttf", "Arial-Bold.ttf", "arialbd.ttf"],
        "Arial.ttf": ["Arial.ttf", "arial.ttf"],
        "Impact.ttf": ["Impact.ttf", "impact.ttf"],
        "Georgia.ttf": ["Georgia.ttf", "georgia.ttf"],
    }
    
    # Try to find the specified font
    if font_name in font_options:
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                for font_file in font_options[font_name]:
                    font_path = os.path.join(font_dir, font_file)
                    if os.path.exists(font_path):
                        return font_path
    
    # Default font fallbacks by platform
    if sys.platform == "darwin":  # macOS
        return "/System/Library/Fonts/SFNS.ttf"  # San Francisco
    elif sys.platform == "win32":  # Windows
        return "C:\\Windows\\Fonts\\arial.ttf"  # Arial
    else:  # Linux and others
        return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # DejaVu Sans

def make_frame_with_text(frame, text, style):
    """Create a frame with styled text overlay"""
    from PIL import Image, ImageDraw, ImageFont
    
    # Convert MoviePy frame to PIL Image
    frame_img = Image.fromarray(frame)
    width, height = frame_img.size
    
    # Create a transparent overlay for text
    overlay = Image.new('RGBA', frame_img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Get font
    font_path = get_system_font(style["font"])
    font = ImageFont.truetype(font_path, style["font_size"])
    
    # Calculate text position
    text_width, text_height = draw.textsize(text, font=font)
    padding = style["highlight_padding"]
    
    if style["position"] == "bottom":
        text_x = (width - text_width) // 2 if style["align"] == "center" else padding
        text_y = height - text_height - padding * 2
    elif style["position"] == "top":
        text_x = (width - text_width) // 2 if style["align"] == "center" else padding
        text_y = padding
    elif style["position"] == "center":
        text_x = (width - text_width) // 2
        text_y = (height - text_height) // 2
    
    # Draw highlight/background if specified
    if style["highlight_color"]:
        # Draw rounded rectangle background
        draw.rounded_rectangle(
            [
                text_x - padding, 
                text_y - padding, 
                text_x + text_width + padding, 
                text_y + text_height + padding
            ],
            radius=padding,
            fill=style["highlight_color"]
        )
    
    # Draw shadow if specified
    if style["shadow"]:
        # Draw text with shadow
        shadow_offset = 2
        draw.text(
            (text_x + shadow_offset, text_y + shadow_offset),
            text,
            font=font,
            fill=(0, 0, 0, 160)  # Semi-transparent black shadow
        )
    
    # Draw main text
    draw.text(
        (text_x, text_y),
        text,
        font=font,
        fill=style["text_color"]
    )
    
    # Composite the text overlay with the original frame
    result = Image.alpha_composite(frame_img.convert('RGBA'), overlay)
    
    # Convert back to RGB for MoviePy
    return np.array(result.convert('RGB'))

@error_handler
def add_captions_to_video(video_path, output_path=None, style_name="tiktok", model_size="base", max_duration=None):
    """
    Add captions to a video with specified style
    
    Args:
        video_path: Path to the video file
        output_path: Path to save the output video
        style_name: Name of caption style to use
        model_size: Whisper model size to use for transcription
        max_duration: Maximum duration in seconds (optional)
        
    Returns:
        dict: Results with status and output path
    """
    if not DEPENDENCIES_AVAILABLE:
        return {"status": "error", "message": "Required dependencies not available"}
    
    # Default output path if none provided
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(video_dir, f"{video_name}_captioned_{timestamp}.mp4")
    
    # Get caption style
    if style_name not in CAPTION_STYLES:
        return {"status": "error", "message": f"Style '{style_name}' not found. Available styles: {', '.join(CAPTION_STYLES.keys())}"}
    
    style = CAPTION_STYLES[style_name]
    
    # Load the video
    try:
        print(f"Loading video: {video_path}")
        video = mp.VideoFileClip(video_path)
        
        # Trim video if max_duration is specified
        if max_duration and video.duration > max_duration:
            video = video.subclip(0, max_duration)
        
        # Transcribe the video to get word-level timing
        transcription = transcribe_video(video_path, model_size=model_size)
        if transcription["status"] != "success":
            return transcription
        
        words = transcription["words"]
        
        # For word-by-word animation
        if style["word_by_word"] and style["animate"]:
            # Create a generator that yields (time, word_to_show) pairs
            def word_generator():
                current_words = []
                current_segment = []
                last_end_time = 0
                
                for i, word in enumerate(words):
                    current_words.append(word["word"])
                    
                    # Add this word to the current segment
                    if len(current_segment) < 7:  # Maximum 7 words per line
                        current_segment.append(word["word"])
                    else:
                        # Start a new segment
                        text = " ".join(current_segment)
                        current_segment = [word["word"]]
                    
                    # Output the current words
                    text = " ".join(current_words[-min(7, len(current_words)):])
                    yield (word["start"], text)
                    
                    # If at the end of the segment or last word, clear after a pause
                    if len(current_segment) >= 7 or i == len(words) - 1:
                        # Stay visible for a bit after the word ends
                        stay_visible = min(0.5, words[i]["end"] - words[i]["start"])
                        yield (word["end"] + stay_visible, "")
                        last_end_time = word["end"] + stay_visible
                    
                # Ensure we cover the full video duration
                if video.duration > last_end_time:
                    yield (video.duration, "")
            
            # Create a list of (t, text) pairs for SubtitlesClip
            subtitles = [(t, text) for t, text in word_generator()]
            
            # Create a function that returns the frame with text overlay at the given time
            def add_caption_to_frame(frame_img, t):
                # Find the subtitle text that should be displayed at time t
                text = ""
                for subtitle_time, subtitle_text in subtitles:
                    if subtitle_time > t:
                        break
                    text = subtitle_text
                
                if text:
                    return make_frame_with_text(frame_img, text, style)
                return frame_img
            
            # Apply the text overlay to the video
            print("Adding animated captions...")
            captioned_video = video.fl(add_caption_to_frame)
            
        else:
            # For segment-by-segment captions (not word-by-word)
            segments = transcription["segments"]
            
            # Create a list of (start_time, end_time, text) for each segment
            segment_subtitles = []
            for segment in segments:
                segment_subtitles.append((
                    segment["start"],
                    segment["end"],
                    segment["text"]
                ))
            
            # Create subtitles function
            def subtitle_generator():
                for start, end, text in segment_subtitles:
                    yield (start, text)
                    yield (end, "")
            
            subtitles = [(t, text) for t, text in subtitle_generator()]
            
            # Create a function that returns the frame with text overlay at the given time
            def add_caption_to_frame(frame_img, t):
                # Find the subtitle text that should be displayed at time t
                text = ""
                for subtitle_time, subtitle_text in subtitles:
                    if subtitle_time > t:
                        break
                    text = subtitle_text
                
                if text:
                    return make_frame_with_text(frame_img, text, style)
                return frame_img
            
            # Apply the text overlay to the video
            print("Adding segment captions...")
            captioned_video = video.fl(add_caption_to_frame)
        
        # Write output video
        print(f"Writing captioned video to: {output_path}")
        captioned_video.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile="temp-audio.m4a",
            remove_temp=True,
            fps=video.fps
        )
        
        # Clean up
        video.close()
        captioned_video.close()
        
        return {
            "status": "success",
            "message": "Captions added successfully",
            "output_path": output_path
        }
    
    except Exception as e:
        print(f"Error adding captions: {str(e)}")
        print(traceback.format_exc())
        return {
            "status": "error",
            "message": f"Error adding captions: {str(e)}",
            "traceback": traceback.format_exc()
        }

def get_available_caption_styles():
    """Return a list of available caption styles with details"""
    return {name: {k: v for k, v in style.items() 
                  if k not in ['font']}  # Exclude font path for cleaner output
            for name, style in CAPTION_STYLES.items()}

if __name__ == "__main__":
    # Simple command-line interface for testing
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        
        # Optional style parameter
        style = "tiktok"
        if len(sys.argv) > 2:
            style = sys.argv[2]
        
        # Check for help flag
        if video_path in ["-h", "--help"]:
            print("Usage: python captions.py [video_path] [style]")
            print(f"Available styles: {', '.join(CAPTION_STYLES.keys())}")
            sys.exit(0)
        
        if not os.path.exists(video_path):
            print(f"Error: Video file not found: {video_path}")
            sys.exit(1)
        
        # Check dependencies
        deps = check_dependencies()
        if not deps["all_available"]:
            print(f"Missing dependencies: {', '.join(deps['missing'])}")
            print("Please install required packages first.")
            sys.exit(1)
        
        # Add captions
        result = add_captions_to_video(video_path, style_name=style)
        
        if result["status"] == "success":
            print(f"Captions added successfully!")
            print(f"Output: {result['output_path']}")
        else:
            print(f"Error adding captions: {result['message']}")
    else:
        print("Please provide a video file path.")
        print("Usage: python captions.py [video_path] [style]") 