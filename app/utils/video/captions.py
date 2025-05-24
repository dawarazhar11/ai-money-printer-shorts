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

# Check if required dependencies are available
DEPENDENCIES_AVAILABLE = True
try:
    import numpy as np
    import moviepy.editor as mp
    from PIL import Image, ImageDraw, ImageFont
    # Import typography effects module
    try:
        from utils.video.typography_effects_pillow import make_frame_with_typography_effects
        TYPOGRAPHY_EFFECTS_AVAILABLE = True
    except ImportError:
        TYPOGRAPHY_EFFECTS_AVAILABLE = False
        
    # Import advanced typography effects module
    try:
        from utils.video.advanced_typography import make_frame_with_advanced_typography
        ADVANCED_TYPOGRAPHY_AVAILABLE = True
    except ImportError:
        ADVANCED_TYPOGRAPHY_AVAILABLE = False
except ImportError:
    DEPENDENCIES_AVAILABLE = False

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

# Add advanced typography effects
ADVANCED_TYPOGRAPHY_EFFECTS = {
    "kinetic_typography": {"description": "Words move independently with unique animations"},
    "audio_reactive": {"description": "Text reacts to audio levels in the video"},
    "character_animation": {"description": "Characters animate individually with effects like drop-in, fade-in, and spin-in"}
}

# Update typography effects dictionary with advanced effects
TYPOGRAPHY_EFFECTS.update(ADVANCED_TYPOGRAPHY_EFFECTS)

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

# Add new advanced caption styles
CAPTION_STYLES.update({
    "kinetic": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": None,  # No background
        "highlight_padding": 15,
        "position": "center",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["kinetic_typography"]  # Use kinetic typography effect
    },
    "audio_pulse": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": (0, 0, 0, 150),  # Semi-transparent black
        "highlight_padding": 15,
        "position": "bottom",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["audio_reactive"]  # Use audio-reactive effect
    },
    "drop_in": {
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
        "typography_effects": ["character_animation"],  # Use character animation effect
        "character_effect": "drop_in"  # Specify the character animation type
    },
    "fade_in": {
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
        "typography_effects": ["character_animation"],  # Use character animation effect
        "character_effect": "fade_in"  # Specify the character animation type
    },
    "spin_in": {
        "font": "Arial-Bold.ttf",
        "font_size": 42,
        "text_color": (255, 255, 255),  # White
        "highlight_color": None,  # No background
        "highlight_padding": 15,
        "position": "center",
        "align": "center",
        "shadow": True,
        "animate": True,
        "word_by_word": True,
        "typography_effects": ["character_animation"],  # Use character animation effect
        "character_effect": "spin_in"  # Specify the character animation type
    }
})

# Also add typography effects to some existing styles
CAPTION_STYLES["tiktok"]["typography_effects"] = ["fade"]
CAPTION_STYLES["modern_bold"]["typography_effects"] = ["scale"]
CAPTION_STYLES["social"]["typography_effects"] = ["fade", "color_shift"]

def get_system_font(font_name):
    """Get a system font or default to Arial"""
    import os
    import sys
    
    # Use more reliable system fonts for macOS
    if sys.platform == "darwin":  # macOS
        # Try user-provided font name first
        if font_name and os.path.exists(font_name):
            return font_name
            
        # macOS system fonts that are more reliable
        if font_name in ["Arial-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]:
            font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
            if os.path.exists(font_path):
                return font_path
        elif font_name in ["Arial.ttf", "arial.ttf"]:
            font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
            if os.path.exists(font_path):
                return font_path
        elif font_name in ["Impact.ttf", "impact.ttf"]:
            font_path = "/System/Library/Fonts/Supplemental/Impact.ttf"
            if os.path.exists(font_path):
                return font_path
    
        # Fallback system fonts on macOS
        fallbacks = [
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/Geneva.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/Library/Fonts/Arial.ttf"
        ]
        for fallback in fallbacks:
            if os.path.exists(fallback):
                return fallback
        return "/System/Library/Fonts/Helvetica.ttc"
        
    # Windows paths
    elif sys.platform == "win32":  # Windows
        font_dir = "C:\\Windows\\Fonts"
        if font_name in ["Arial-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]:
            return os.path.join(font_dir, "arialbd.ttf")
        elif font_name in ["Arial.ttf", "arial.ttf"]:
            return os.path.join(font_dir, "arial.ttf")
        elif font_name in ["Impact.ttf", "impact.ttf"]:
            return os.path.join(font_dir, "impact.ttf")
        else:
            # Fallback to Arial
            return os.path.join(font_dir, "arial.ttf")
    
    # Linux and others
    else:
        # Try to use DejaVu fonts which are commonly available
        if font_name in ["Arial-Bold.ttf", "Arial Bold.ttf", "arialbd.ttf"]:
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        elif font_name in ["Arial.ttf", "arial.ttf"]:
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        elif font_name in ["Impact.ttf", "impact.ttf"]:
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
        else:
            # Fallback
            return "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

def make_frame_with_text(frame_img, text, words_with_times, current_time, style, effect_params=None):
    """Apply text to a video frame with timing-aware effects"""
    from PIL import ImageDraw, ImageFont, Image
    import numpy as np
    import sys
    
    # Skip if no text
    if not text or not text.strip():
        return frame_img
    
    # Check if we should use advanced typography effects from style
    typography_effects = style.get("typography_effects", [])
    if typography_effects:
        try:
            # Try to import advanced typography module
            from utils.video.advanced_typography import (
                make_frame_with_advanced_typography,
                apply_kinetic_typography,
                apply_audio_reactive_text,
                apply_character_animation
            )
    
            # Get font path
            font_path = get_system_font(style.get("font", "Arial Bold.ttf"))
    
            # Get or compute font size
            font_size = style.get("font_size", 40)
            
            # Get position
            position = style.get("position", "bottom")
            
            # Determine audio level (if needed)
            audio_level = None
            if "audio_reactive" in typography_effects and effect_params and "audio_level" in effect_params:
                audio_level = effect_params.get("audio_level", 0.5)
            
            # Apply advanced typography effects
            return make_frame_with_advanced_typography(
                frame=frame_img,
                text=text,
                font_path=font_path,
                font_size=font_size,
                current_time=current_time,
                word_timing=words_with_times,
                effects=typography_effects,
                style=style,
                audio_data=audio_level
            )
        except ImportError as e:
            print(f"WARNING: Advanced typography module not available: {e}")
            # Fall back to standard text rendering
    
    # Ensure frame_img is a numpy array
    try:
        if not isinstance(frame_img, np.ndarray):
            frame_img = np.array(frame_img)
    except Exception as e:
        print(f"ERROR in make_frame_with_text: {e}")
        # Return a black frame as fallback
        return np.zeros((720, 1280, 3), dtype=np.uint8)
    
    # Convert to PIL Image for drawing
    frame_pil = Image.fromarray(frame_img)
    
    # Make sure we have an RGBA image for proper alpha handling
    if frame_pil.mode != 'RGBA':
        frame_pil = frame_pil.convert('RGBA')
    
    # Get frame dimensions
    width, height = frame_pil.size
    
    # Create a transparent overlay for the text
    text_overlay = Image.new('RGBA', frame_pil.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_overlay)
    
    # Get font - either from style or use a default
    font_path = get_system_font(style.get("font", "Arial Bold.ttf"))
            
    # Get or compute font size
    font_size = style.get("font_size", int(height * 0.05))  # 5% of height as default
    
    # Static variable to track if we've already logged about finding this font
    if not hasattr(make_frame_with_text, "logged_fonts"):
        make_frame_with_text.logged_fonts = set()
    
    try:
        font = ImageFont.truetype(font_path, font_size)
        # Only log each font path once to reduce console spam
        if font_path not in make_frame_with_text.logged_fonts:
            print(f"DEBUG: Found system font: {font_path}")
            make_frame_with_text.logged_fonts.add(font_path)
    except Exception as e:
        print(f"Warning: Could not load font {font_path}: {e}")
        # Fallback to default font
        try:
            # Try PIL's default font
            font = ImageFont.load_default()
        except:
            # If all else fails, just return the original frame
            return frame_img
    
    # Get text properties from style
    text_color = style.get("text_color", (255, 255, 255))
    bg_color = style.get("highlight_color", None)
    position = style.get("position", "bottom")
    padding = style.get("highlight_padding", 15)
    
    # Simple text positioning based on the position setting
    if position == "top":
        y_position = padding
    elif position == "middle":
        y_position = height // 2
    else:  # bottom (default)
        y_position = height - (font_size * 2) - padding
    
    # Calculate text width and center horizontally
    try:
        # Try newer Pillow 10.0+ method first
        text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
    except (AttributeError, TypeError):
        try:
            # Fall back to older method
            text_width, text_height = draw.textsize(text, font=font)
        except (AttributeError, TypeError):
            # Last resort fallback - estimate based on font size
            text_width, text_height = len(text) * font.size * 0.6, font.size * 1.2
    
    x_position = (width - text_width) // 2
    
    # Draw text background if specified
    if bg_color:
        # Convert to RGBA if needed
        if len(bg_color) == 3:
            bg_color = (*bg_color, 180)  # Add alpha
            
        # Draw rounded rectangle for background
        draw.rectangle(
            [
                x_position - padding,
                y_position - padding,
                x_position + text_width + padding,
                y_position + text_height + padding
            ],
            fill=bg_color
        )
    
    # Draw the text
    draw.text((x_position, y_position), text, font=font, fill=text_color)
    
    # Composite the text overlay with the original frame
    result = Image.alpha_composite(frame_pil, text_overlay)
    
    # Convert back to RGB for compatibility with video frames
    result = result.convert('RGB')
    
    # Convert back to numpy array and ensure correct format
    result_array = np.array(result)
    return result_array

def add_caption_to_frame(frame, text, word_info, current_time, style, effect_params=None):
    """Add caption to a single video frame with current word timing"""
    try:
        # Skip if no text or empty text
        if not text or not text.strip():
            return frame
            
        # Call make_frame_with_text and pass only the parameters it accepts
        return make_frame_with_text(
            frame_img=frame,
            text=text,
            words_with_times=word_info.get("words_with_times", []) if word_info else [],
            current_time=current_time,
            style=style,
            effect_params=effect_params
        )
    except Exception as e:
        print(f"Error in add_caption_to_frame: {e}")
        return frame

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
            print(f"DEBUG: Using custom style with keys: {list(style.keys())}")
            if "typography_effects" in style:
                print(f"DEBUG: Custom style has typography effects: {style['typography_effects']}")
        elif style_name not in CAPTION_STYLES:
            return {"status": "error", "message": f"Style '{style_name}' not found. Available styles: {', '.join(CAPTION_STYLES.keys())}"}
        else:
            style = CAPTION_STYLES[style_name]
            print(f"DEBUG: Using predefined style '{style_name}' with keys: {list(style.keys())}")
            if "typography_effects" in style:
                print(f"DEBUG: Style has typography effects: {style['typography_effects']}")
        
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
            def create_caption_frame(frame_img, t):
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
                        return add_caption_to_frame(
                            frame_img, 
                            current_text, 
                            current_word_info, 
                            t,
                            style
                        )
                    return frame_img
                except Exception as e:
                    print(f"Error in create_caption_frame: {str(e)}")
                    return frame_img
            
            # Apply the text overlay to the video
            print("Adding animated captions...")
            
            # Apply the function to each frame
            captioned_video = video.fl(lambda gf, t: create_caption_frame(gf(t), t))
            
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
                    return add_caption_to_frame(
                        frame,
                        text,
                        None,
                        t,
                        style
                    )
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

def get_caption_style(style_name=None, custom_style=None):
    """
    Get caption style by name or custom parameters
    
    Args:
        style_name: Name of caption style
        custom_style: Custom style parameters
        
    Returns:
        dict: Caption style parameters
    """
    # Use custom style if provided
    if custom_style is not None:
        return custom_style
    
    # Use default style if no style name provided
    if style_name is None or style_name not in CAPTION_STYLES:
        return CAPTION_STYLES["tiktok"]
    
    # Return the style
    return CAPTION_STYLES[style_name]

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