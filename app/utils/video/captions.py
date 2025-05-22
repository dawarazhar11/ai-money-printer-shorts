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
import math

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
    # Check if any transcription engine is available
    try:
        from utils.audio.transcription import transcribe_video as transcription_func
        TRANSCRIPTION_AVAILABLE = True
        print("✅ Successfully imported transcription module")
    except ImportError:
        # Try to import whisper directly as fallback
        try:
            import whisper
            TRANSCRIPTION_AVAILABLE = True
            print("✅ Successfully imported whisper module")
        except ImportError:
            TRANSCRIPTION_AVAILABLE = False
            print("❌ No transcription module available")

    from PIL import Image, ImageDraw, ImageFont
    DEPENDENCIES_AVAILABLE = True
    print("✅ Successfully imported caption dependencies")
except ImportError as e:
    DEPENDENCIES_AVAILABLE = False
    TRANSCRIPTION_AVAILABLE = False
    print(f"❌ Error importing caption dependencies: {str(e)}")
    print("Please run the dependencies installation to use caption features")

# Helper function to get text size compatible with all Pillow versions
def get_text_size(draw, text, font):
    """
    Get text size in a way that works with older and newer versions of Pillow
    
    Args:
        draw: ImageDraw object
        text: Text string
        font: Font to use
        
    Returns:
        tuple: (width, height) of text
    """
    try:
        # Try newer Pillow 10.0+ method first
        return draw.textbbox((0, 0), text, font=font)[2:]
    except (AttributeError, TypeError):
        try:
            # Fall back to older method
            return draw.textsize(text, font=font)
        except (AttributeError, TypeError):
            # Last resort fallback - estimate based on font size
            return (len(text) * font.size * 0.6, font.size * 1.2)

def check_dependencies():
    """Check if all required dependencies are installed"""
    missing = []
    
    try:
        import moviepy.editor as mp
    except ImportError:
        missing.append("moviepy")
    
    # Check if any transcription engine is available
    transcription_available = False
    try:
        from utils.audio.transcription import check_module_availability
        # Check whisper
        if check_module_availability("whisper"):
            transcription_available = True
        # Check vosk
        elif check_module_availability("vosk"):
            transcription_available = True
    except ImportError:
        # Fallback check for whisper directly
        try:
            import whisper
            transcription_available = True
        except ImportError:
            pass
    
    if not transcription_available:
        missing.append("transcription (whisper or vosk)")
    
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
def transcribe_video(video_path, model_size="base", engine="auto"):
    """
    Transcribe video audio to text with timestamps
    
    Args:
        video_path: Path to the video file
        model_size: Model size for Whisper (tiny, base, small, medium, large)
        engine: Transcription engine to use ("whisper", "vosk", or "auto")
        
    Returns:
        dict: Results containing transcript with word-level timing
    """
    if not DEPENDENCIES_AVAILABLE or not TRANSCRIPTION_AVAILABLE:
        return {"status": "error", "message": "Required dependencies not available"}
    
    try:
        # Validate the video path
        if not video_path:
            return {"status": "error", "message": "No video path provided"}
            
        if not os.path.exists(video_path):
            return {"status": "error", "message": f"Video file not found: {video_path}"}
            
        # Check if the new transcription API is available
        try:
            from utils.audio.transcription import transcribe_video as transcription_func
            print(f"Using transcription API with engine={engine}, model_size={model_size}")
            
            # Call the transcription API
            result = transcription_func(
                video_path, 
                engine=engine, 
                model_size=model_size if engine == "whisper" else None
            )
            
            # Format the result to match the expected output
            if "error" in result:
                return {"status": "error", "message": result["error"]}
            
            # Create a standard response format regardless of engine
            if engine == "vosk" or result.get("engine") == "vosk":
                # Format Vosk results to match the expected whisper format
                segments = result.get("segments", [])
                words = []
                
                for segment in segments:
                    segment_words = segment.get("words", [])
                    for word_info in segment_words:
                        words.append({
                            "word": word_info.get("word", ""),
                            "start": word_info.get("start", 0),
                            "end": word_info.get("end", 0)
                        })
                
                return {
                    "status": "success",
                    "transcript": result.get("text", ""),
                    "segments": segments,
                    "words": words,
                    "engine": "vosk"
                }
            else:
                # Already in Whisper format or compatible
                return {
                    "status": "success",
                    "transcript": result.get("text", ""),
                    "segments": result.get("segments", []),
                    "words": [
                        {
                            "word": word.get("word", ""),
                            "start": word.get("start", 0),
                            "end": word.get("end", 0)
                        }
                        for word in result.get("words", [])
                    ],
                    "engine": "whisper"
                }
                
        except ImportError:
            # Fall back to direct whisper usage
            print(f"Using direct Whisper API with model_size={model_size}")
            import whisper
            
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
                ],
                "engine": "whisper"
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

# Add new typography effects constants
TYPOGRAPHY_EFFECTS = {
    "fade": {
        "description": "Fade in/out effect for each word",
        "params": {
            "fade_in_duration": 0.2,  # seconds
            "fade_out_duration": 0.1  # seconds
        }
    },
    "scale": {
        "description": "Scale words up/down for emphasis",
        "params": {
            "min_scale": 0.8,
            "max_scale": 1.5,
            "scale_duration": 0.3  # seconds
        }
    },
    "color_shift": {
        "description": "Shift colors based on word importance",
        "params": {
            "regular_color": (255, 255, 255),  # White
            "emphasis_color": (255, 255, 0),   # Yellow
            "strong_emphasis_color": (255, 150, 0)  # Orange
        }
    },
    "wave": {
        "description": "Words move in a wave pattern",
        "params": {
            "amplitude": 10,  # pixels
            "frequency": 2.0  # cycles per second
        }
    },
    "typewriter": {
        "description": "Words appear one character at a time",
        "params": {
            "chars_per_second": 15
        }
    }
}

# Update the caption styles to include typography effects
CAPTION_STYLES.update({
    "dynamic": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 180),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["fade", "scale"]  # List of effects to apply
    },
    "impactful": {
        "font": "Impact.ttf",
        "font_size": 45,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 200),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "center",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["scale", "color_shift"]  # List of effects to apply
    },
    "wave_text": {
        "font": "Arial-Bold.ttf",
        "font_size": 40,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 100, 180),  # Semi-transparent blue
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["wave"]  # List of effects to apply
    },
    "typewriter": {
        "font": "Courier New.ttf",
        "font_size": 38,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 200),  # Semi-transparent black
        "highlight_padding": 12,
        "position": "bottom",
        "align": "center",
        "shadow": False,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["typewriter"]  # List of effects to apply
    }
})

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
                        print(f"DEBUG: Found system font: {font_path}")
                        return font_path
    
    # Default font fallbacks by platform
    if sys.platform == "darwin":  # macOS
        fallbacks = [
            "/System/Library/Fonts/SFNS.ttf",  # San Francisco
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Geneva.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/Library/Fonts/Arial.ttf"
        ]
        for fallback in fallbacks:
            if os.path.exists(fallback):
                print(f"DEBUG: Using fallback macOS font: {fallback}")
                return fallback
        return "/System/Library/Fonts/SFNS.ttf"  # Default fallback even if it doesn't exist
    elif sys.platform == "win32":  # Windows
        return "C:\\Windows\\Fonts\\arial.ttf"  # Arial
    else:  # Linux and others
        return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # DejaVu Sans

def make_simple_frame_with_text(frame_img, text, style):
    """Original function for simple text overlay without effects"""
    from PIL import ImageDraw, ImageFont, Image
    import numpy as np
    
    # Ensure input is a numpy array
    if not isinstance(frame_img, np.ndarray):
        try:
            frame_img = np.array(frame_img)
        except:
            # Return a black frame if conversion fails
            return np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Skip if no text
    if not text or not text.strip():
        return frame_img
    
    # Convert to PIL Image
    frame_pil = Image.fromarray(frame_img)
    
    # Create a drawing context
    draw = ImageDraw.Draw(frame_pil)
    
    # Get font and calculate text position
    font_path = get_system_font(style["font"])
    print(f"DEBUG: Using font path: {font_path}")
    font = ImageFont.truetype(font_path, style["font_size"])
    text_width, text_height = get_text_size(draw, text, font)
    padding = style["highlight_padding"]
    
    # Calculate text position
    if style["position"] == "bottom":
        text_x = (frame_pil.width - text_width) // 2 if style["align"] == "center" else padding
        text_y = frame_pil.height - text_height - padding * 2
    elif style["position"] == "top":
        text_x = (frame_pil.width - text_width) // 2 if style["align"] == "center" else padding
        text_y = padding
    else:  # center
        text_x = (frame_pil.width - text_width) // 2
        text_y = (frame_pil.height - text_height) // 2
    
    # Draw highlight/background if specified
    if style["highlight_color"]:
        # Get highlight color
        highlight_color = style["highlight_color"]
        if len(highlight_color) == 3:
            highlight_color = highlight_color + (180,)  # Add alpha
        
        # Draw background with rounded corners
        draw.rounded_rectangle(
            [
                text_x - padding, 
                text_y - padding, 
                text_x + text_width + padding, 
                text_y + text_height + padding
            ],
            radius=padding,
            fill=highlight_color[:3]  # Remove alpha for PIL drawing
        )
    
    # Draw shadow if specified
    if style["shadow"]:
        shadow_offset = 2
        draw.text(
            (text_x + shadow_offset, text_y + shadow_offset),
            text,
            font=font,
            fill=(0, 0, 0)
        )
    
    # Draw the text
    text_color = style["text_color"]
    draw.text(
        (text_x, text_y),
        text,
        font=font,
        fill=text_color[:3] if len(text_color) > 3 else text_color
    )
    
    # Convert back to numpy array
    return np.array(frame_pil)

def make_frame_with_text(frame, text, style, word_info=None, current_time=0, is_active=True):
    """Create a frame with styled text overlay including typography effects"""
    from PIL import Image
    import numpy as np
    
    try:
        # Convert MoviePy frame to numpy array
        if callable(frame):
            frame = frame(current_time)
            
        # Ensure frame is a numpy array
        if not isinstance(frame, np.ndarray):
            print(f"Warning: frame is not a numpy array, but {type(frame)}")
            return frame
        
        # Skip if no text
        if not text or not text.strip():
            return frame
        
        # Debug info
        print(f"DEBUG: Drawing text '{text}' at time {current_time}")
        
        # Apply typography effects if style has them, otherwise use simple text
        if "typography_effects" in style and style["typography_effects"]:
            # Use the typography effects
            result = simple_typography_effects(frame, text, style, word_info, current_time, is_active)
        else:
            # Use simple text overlay
            result = make_simple_frame_with_text(frame, text, style)
        
        # Debug: save the first frame
        if int(current_time) == 0:
            try:
                Image.fromarray(result).save("debug_caption_frame.png")
                print("DEBUG: Saved debug_caption_frame.png")
            except Exception as e:
                print(f"DEBUG: Could not save debug frame: {e}")
        
        return result
    except Exception as e:
        print(f"ERROR in make_frame_with_text: {e}")
        # Return the original frame on error
        return frame

def simple_typography_effects(frame, text, style, word_info=None, current_time=0, is_active=True):
    """Simplified version of typography effects that works reliably"""
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
    import math
    
    # Skip if no text
    if not text or not text.strip():
        return frame
    
    # Convert to PIL Image
    frame_pil = Image.fromarray(frame)
    
    # Create drawing context
    draw = ImageDraw.Draw(frame_pil)
    
    # Get the base font
    font_path = get_system_font(style["font"])
    font_size = style["font_size"]
    
    # Get available effects
    effects = style.get("typography_effects", [])
    
    # Initialize effect parameters
    opacity = 1.0 if is_active else 0.5
    scale_factor = 1.0
    text_color = style["text_color"]
    x_offset = 0
    y_offset = 0
    
    # Apply effects if word timing is available
    if word_info and "start" in word_info and "end" in word_info and is_active:
        word_start = word_info["start"]
        word_end = word_info["end"]
        word_duration = max(0.1, word_end - word_start)  # Ensure duration is not zero
        time_in_word = current_time - word_start
        
        # Apply fade effect
        if "fade" in effects:
            fade_in_duration = TYPOGRAPHY_EFFECTS["fade"]["params"]["fade_in_duration"]
            fade_out_duration = TYPOGRAPHY_EFFECTS["fade"]["params"]["fade_out_duration"]
            
            if time_in_word < fade_in_duration:
                # Fade in
                opacity = min(1.0, time_in_word / fade_in_duration)
            elif time_in_word > word_duration - fade_out_duration:
                # Fade out
                time_to_end = word_duration - time_in_word
                opacity = max(0.0, time_to_end / fade_out_duration)
        
        # Apply scale effect
        if "scale" in effects:
            min_scale = TYPOGRAPHY_EFFECTS["scale"]["params"]["min_scale"]
            max_scale = TYPOGRAPHY_EFFECTS["scale"]["params"]["max_scale"]
            scale_duration = TYPOGRAPHY_EFFECTS["scale"]["params"]["scale_duration"]
            
            if time_in_word < scale_duration:
                # Scale up at the beginning
                progress = time_in_word / scale_duration
                scale_factor = min_scale + (max_scale - min_scale) * progress
            elif time_in_word > word_duration - scale_duration:
                # Scale down at the end
                progress = (word_duration - time_in_word) / scale_duration
                scale_factor = min_scale + (max_scale - min_scale) * progress
            else:
                # Maintain max scale in the middle
                scale_factor = max_scale
        
        # Apply color shift effect
        if "color_shift" in effects:
            regular_color = TYPOGRAPHY_EFFECTS["color_shift"]["params"]["regular_color"]
            emphasis_color = TYPOGRAPHY_EFFECTS["color_shift"]["params"]["emphasis_color"]
            strong_emphasis_color = TYPOGRAPHY_EFFECTS["color_shift"]["params"]["strong_emphasis_color"]
            
            # Use emphasis color in the middle of the word duration
            mid_point = word_duration / 2
            distance_from_mid = abs(time_in_word - mid_point)
            color_shift_threshold = word_duration / 4
            
            if distance_from_mid < color_shift_threshold:
                # Use strong emphasis near the middle
                text_color = strong_emphasis_color
            elif distance_from_mid < color_shift_threshold * 2:
                # Use regular emphasis a bit further from middle
                text_color = emphasis_color
            else:
                # Use regular color toward beginning and end
                text_color = regular_color
        
        # Apply wave effect
        if "wave" in effects:
            amplitude = TYPOGRAPHY_EFFECTS["wave"]["params"]["amplitude"]
            frequency = TYPOGRAPHY_EFFECTS["wave"]["params"]["frequency"]
            
            # Create a wave motion based on time
            progress = time_in_word / word_duration
            wave_position = progress * 2 * 3.1416 * frequency
            y_offset = amplitude * math.sin(wave_position)
    
    # Apply the calculated font size with scaling
    scaled_font_size = max(10, int(font_size * scale_factor))
    font = ImageFont.truetype(font_path, scaled_font_size)
    
    # Calculate text position
    text_width, text_height = get_text_size(draw, text, font)
    padding = style["highlight_padding"]
    
    if style["position"] == "bottom":
        text_x = (frame_pil.width - text_width) // 2 if style["align"] == "center" else padding
        text_y = frame_pil.height - text_height - padding * 2
    elif style["position"] == "top":
        text_x = (frame_pil.width - text_width) // 2 if style["align"] == "center" else padding
        text_y = padding
    else:  # center
        text_x = (frame_pil.width - text_width) // 2
        text_y = (frame_pil.height - text_height) // 2
    
    # Apply offsets
    text_x += int(x_offset)
    text_y += int(y_offset)
    
    # Draw highlight/background if specified
    if style["highlight_color"]:
        highlight_color = style["highlight_color"]
        # Apply opacity
        if opacity < 1.0:
            # Use a lighter color for less opacity (since we can't use alpha)
            if len(highlight_color) == 4:
                # Already has alpha
                r, g, b, a = highlight_color
                a = int(a * opacity)
                highlight_color = (r, g, b)
            else:
                r, g, b = highlight_color
                # Blend with white for lower opacity
                r = int(r + (255 - r) * (1 - opacity))
                g = int(g + (255 - g) * (1 - opacity))
                b = int(b + (255 - b) * (1 - opacity))
                highlight_color = (r, g, b)
        
        # Draw background
        draw.rounded_rectangle(
            [
                text_x - padding, 
                text_y - padding, 
                text_x + text_width + padding, 
                text_y + text_height + padding
            ],
            radius=padding,
            fill=highlight_color[:3]  # Ensure only RGB is used
        )
    
    # Draw shadow if specified
    if style["shadow"]:
        shadow_offset = int(2 * scale_factor)
        # Use a darker shadow for lower opacity
        shadow_color = (0, 0, 0) if opacity > 0.7 else (50, 50, 50)
        draw.text(
            (text_x + shadow_offset, text_y + shadow_offset),
            text,
            font=font,
            fill=shadow_color
        )
    
    # Apply typewriter effect if specified
    if "typewriter" in effects and word_info and "start" in word_info and is_active:
        chars_per_second = TYPOGRAPHY_EFFECTS["typewriter"]["params"]["chars_per_second"]
        word_start = word_info["start"]
        time_in_word = current_time - word_start
        
        # Calculate how many characters should be visible
        visible_chars = int(time_in_word * chars_per_second)
        
        if 0 < visible_chars < len(text):
            # Show only the visible characters
            text = text[:visible_chars]
            # Recalculate text width for partial text
            text_width, _ = get_text_size(draw, text, font)
    
    # Apply opacity to text color
    if opacity < 1.0:
        # Blend with white for text
        r, g, b = text_color[:3]
        r = int(r + (255 - r) * (1 - opacity))
        g = int(g + (255 - g) * (1 - opacity))
        b = int(b + (255 - b) * (1 - opacity))
        text_color = (r, g, b)
    
    # Draw the text
    draw.text(
        (text_x, text_y),
        text,
        font=font,
        fill=text_color[:3] if len(text_color) > 3 else text_color
    )
    
    # Convert back to numpy array
    return np.array(frame_pil)

@error_handler
def add_captions_to_video(video_path, output_path=None, style_name="tiktok", model_size="base", engine="auto", max_duration=None, custom_style=None):
    """
    Add captions to a video with specified style
    
    Args:
        video_path: Path to the video file
        output_path: Path to save the output video
        style_name: Name of caption style to use
        model_size: Model size to use for transcription
        engine: Transcription engine to use ("whisper", "vosk", or "auto")
        max_duration: Maximum duration in seconds (optional)
        custom_style: Optional custom style dictionary to override the named style
        
    Returns:
        dict: Results with status and output path
    """
    import math  # Add import for math functions
    
    # Make sure this function returns a dictionary, not a generator
    try:
        if not DEPENDENCIES_AVAILABLE:
            return {"status": "error", "message": "Required dependencies not available"}
        
        # Validate video path
        if not video_path:
            return {"status": "error", "message": "No video path provided"}
            
        if not os.path.exists(video_path):
            return {"status": "error", "message": f"Video file not found: {video_path}"}
        
        # Default output path if none provided
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            video_dir = os.path.dirname(video_path)
            video_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = os.path.join(video_dir, f"{video_name}_captioned_{timestamp}.mp4")
        
        # Get caption style
        if custom_style:
            style = custom_style
        elif style_name not in CAPTION_STYLES:
            return {"status": "error", "message": f"Style '{style_name}' not found. Available styles: {', '.join(CAPTION_STYLES.keys())}"}
        else:
            style = CAPTION_STYLES[style_name]
        
        # Load the video
        print(f"Loading video: {video_path}")
        video = mp.VideoFileClip(video_path)
        
        # Trim video if max_duration is specified
        if max_duration and video.duration > max_duration:
            video = video.subclip(0, max_duration)
        
        # Transcribe the video to get word-level timing
        transcription = transcribe_video(video_path, model_size=model_size, engine=engine)
        if transcription["status"] != "success":
            return transcription
        
        words = transcription["words"]
        print(f"DEBUG: Transcription returned {len(words)} words")
        
        # If no words were transcribed, create a fallback caption
        if not words:
            print("WARNING: No words found in transcription. Creating a fallback caption.")
            # Create a fallback word that covers the entire video duration
            fallback_word = {
                "word": "No speech detected",
                "start": 0,
                "end": video.duration
            }
            words = [fallback_word]
            print(f"DEBUG: Created fallback caption covering 0 to {video.duration} seconds")
        
        # For word-by-word animation
        if style["word_by_word"] and style["animate"]:
            # Create a list that stores (time, word_to_show) pairs
            animation_data = []
            current_words = []
            current_segment = []
            last_end_time = 0
            
            print("DEBUG: Creating animation data from words:")
            print(f"DEBUG: Found {len(words)} words in transcript")
            
            # Special case: If no words are found, still need empty animation data
            if not words:
                animation_data.append((0, "", None))
                animation_data.append((video.duration, "", None))
            else:
                # Sort words by start time to ensure proper sequence
                words.sort(key=lambda w: w["start"])
                
                # Process all words in transcript
                for i, word in enumerate(words):
                    # Debug for first 5 words
                    if i < 5:
                        print(f"DEBUG: Processing word {i}: '{word['word']}' ({word['start']:.2f}s - {word['end']:.2f}s)")
                    
                    # Make sure start time is not before the last end time (avoid overlaps)
                    start_time = max(word["start"], last_end_time)
                    end_time = max(word["end"], start_time + 0.1)  # Ensure minimum duration
                    
                    # If there's a gap between the last end time and this start time, add empty text
                    if start_time > last_end_time + 0.1 and i > 0:
                        animation_data.append((last_end_time, "", None))
                        animation_data.append((start_time, "", None))
                        current_words = []  # Reset current words for a fresh segment
                    
                    # Add this word to current words list and segment
                    current_words.append(word["word"])
                    
                    # Add this word to the current segment
                    if len(current_segment) < 7:  # Maximum 7 words per line
                        current_segment.append(word["word"])
                    else:
                        # Start a new segment
                        current_segment = [word["word"]]
                    
                    # Output the current words (up to 7 most recent)
                    display_words = current_words[-min(7, len(current_words)):]
                    text = " ".join(display_words)
                    
                    # Add entry at the start time of this word
                    animation_data.append((start_time, text, word))
                    
                    # Update the last end time
                    last_end_time = end_time
                    
                    # If at the end of the segment or last word, add a blank entry after a pause
                    if len(current_segment) >= 7 or i == len(words) - 1:
                        # Stay visible for a bit after the word ends
                        stay_visible = min(0.5, end_time - start_time)
                        animation_data.append((end_time + stay_visible, "", None))
                        last_end_time = end_time + stay_visible
                
                # Ensure we cover the full video duration
                if video.duration > last_end_time:
                    animation_data.append((last_end_time, "", None))
                    animation_data.append((video.duration, "", None))
            
            # Debug the first few animation data entries
            print("DEBUG: Animation data (first 10 entries):")
            for i, (time_point, text, word_info) in enumerate(animation_data[:10]):
                if word_info:
                    print(f"  {i}: {time_point:.2f}s - '{text}' (word: '{word_info.get('word', '')}')")
                else:
                    print(f"  {i}: {time_point:.2f}s - '{text}' (word: None)")
            
            # Create a function that returns the frame with text overlay at the given time
            def add_caption_to_frame(frame_img, t):
                # Find the currently active word and text to display
                current_text = ""
                current_word_info = None
                is_active = False
                
                try:
                    # Loop through all animation entries to find the one that contains the current time
                    # Find the last entry where time_point <= t
                    matching_index = -1
                    for i, (time_point, text, word_info) in enumerate(animation_data):
                        if time_point <= t:
                            matching_index = i
                        else:
                            break
                    
                    # If we found a matching index, use that entry
                    if matching_index >= 0:
                        current_text = animation_data[matching_index][1]
                        current_word_info = animation_data[matching_index][2]
                        is_active = True
                        if t < 0.5:  # Only debug early frames
                            print(f"DEBUG: Found text for time {t}: '{current_text}' at index {matching_index}")
                    
                    # Special case for first frame
                    if t == 0 and animation_data and animation_data[0][0] == 0:
                        current_text = animation_data[0][1]
                        current_word_info = animation_data[0][2]
                        is_active = True
                        print(f"DEBUG: Using first animation entry for time 0: '{current_text}'")
                    
                    if current_text:
                        return make_frame_with_text(
                            frame_img, 
                            current_text,
                            style, 
                            word_info=current_word_info, 
                            current_time=t,
                            is_active=is_active
                        )
                    return frame_img
                except Exception as e:
                    print(f"Error in add_caption_to_frame: {str(e)}")
                    return frame_img
            
            # Apply the text overlay to the video
            print("Adding animated captions...")
            
            # Apply the function to each frame
            captioned_video = video.fl(lambda gf, t: add_caption_to_frame(gf(t), t))
            
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
            
            # Create subtitles list
            subtitles = []
            for start, end, text in segment_subtitles:
                subtitles.append((start, text))
                subtitles.append((end, ""))
            
            # Apply the function to each frame
            def process_frame_with_subtitles(frame, t):
                # Find the subtitle text that should be displayed at time t
                text = ""
                for subtitle_time, subtitle_text in subtitles:
                    if subtitle_time > t:
                        break
                    text = subtitle_text
                
                if text:
                    return make_frame_with_text(frame, text, style, current_time=t)
                return frame
            
            # Apply the text overlay to the video
            print("Adding segment captions...")
            captioned_video = video.fl(lambda gf, t: process_frame_with_subtitles(gf(t), t))
        
        # Write output video
        print(f"Writing captioned video to: {output_path}")
        try:
            captioned_video.write_videofile(
                output_path,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile="temp-audio.m4a",
                remove_temp=True,
                fps=video.fps,
                logger=None  # Use default logger
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
            print(f"Error writing output video: {str(e)}")
            print(traceback.format_exc())
            
            # Attempt to clean up resources even if there was an error
            try:
                video.close()
            except:
                pass
                
            try:
                captioned_video.close()
            except:
                pass
                
            return {
                "status": "error",
                "message": f"Error writing output video: {str(e)}",
                "traceback": traceback.format_exc()
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