#!/usr/bin/env python3
"""
Typography effects implementation for captions
This module provides handlers for various text effects that can be applied to captions
"""

import math
from PIL import Image, ImageDraw, ImageFont

def apply_fade_effect(text, font, current_time, word_timing, params=None):
    """
    Apply a fade effect to text based on word timing
    
    Args:
        text (str): The text to render
        font (ImageFont): The font to use
        current_time (float): Current video time in seconds
        word_timing (dict): Dictionary with word timing info
        params (dict): Optional parameters to customize the effect
        
    Returns:
        tuple: (text_image, opacity)
    """
    # Default parameters
    default_params = {
        "fade_in_duration": 0.2,  # seconds
        "fade_out_duration": 0.1,  # seconds
        "min_opacity": 0.0,
        "max_opacity": 1.0,
        "fade_between_words": True
    }
    
    # Use provided params or defaults
    if params is None:
        params = {}
    
    # Merge with defaults
    for key, value in default_params.items():
        if key not in params:
            params[key] = value
    
    # Get word timing info
    words = word_timing if isinstance(word_timing, list) else word_timing.get("words", [])
    if not words:
        # If no word timing, return full opacity
        return None, 1.0
    
    # Find the currently active word
    active_word = None
    next_word = None
    
    for i, word in enumerate(words):
        word_start = word.get("start", 0)
        word_end = word.get("end", word_start + 0.5)
        
        # Check if this word is active
        if word_start <= current_time <= word_end + params["fade_out_duration"]:
            active_word = word
            # Get next word if available
            if i < len(words) - 1:
                next_word = words[i + 1]
            break
    
    # If no active word found, return zero opacity
    if active_word is None:
        return None, 0.0
    
    # Calculate opacity based on timing
    word_start = active_word.get("start", 0)
    word_end = active_word.get("end", word_start + 0.5)
    
    # Fade in
    if current_time < word_start + params["fade_in_duration"]:
        progress = (current_time - word_start) / params["fade_in_duration"]
        opacity = params["min_opacity"] + (params["max_opacity"] - params["min_opacity"]) * progress
    
    # Fade out
    elif current_time > word_end:
        progress = (current_time - word_end) / params["fade_out_duration"]
        opacity = params["max_opacity"] - (params["max_opacity"] - params["min_opacity"]) * progress
    
    # Full opacity during word
    else:
        opacity = params["max_opacity"]
    
    # Ensure opacity is within bounds
    opacity = max(params["min_opacity"], min(params["max_opacity"], opacity))
    
    # If we're fading between words, adjust opacity when approaching next word
    if params["fade_between_words"] and next_word:
        next_word_start = next_word.get("start", 0)
        time_to_next = next_word_start - current_time
        
        # If we're close to the next word, start fading out
        if 0 < time_to_next < params["fade_out_duration"]:
            next_opacity = params["min_opacity"] + (params["max_opacity"] - params["min_opacity"]) * (time_to_next / params["fade_out_duration"])
            opacity = min(opacity, next_opacity)
    
    return None, opacity

def apply_scale_effect(text, font, current_time, word_timing, params=None):
    """
    Apply a scale effect to text based on word timing and importance
    
    Args:
        text (str): The text to render
        font (ImageFont): The font to use
        current_time (float): Current video time in seconds
        word_timing (dict): Dictionary with word timing info
        params (dict): Optional parameters to customize the effect
        
    Returns:
        tuple: (scale_factor, position_offset)
    """
    # Default parameters
    default_params = {
        "min_scale": 0.8,
        "max_scale": 1.5,
        "scale_duration": 0.3,  # seconds
        "emphasize_keywords": True,
        "keywords": ["important", "key", "critical", "essential", "significant", "major"],
        "emphasis_scale": 1.3
    }
    
    # Use provided params or defaults
    if params is None:
        params = {}
    
    # Merge with defaults
    for key, value in default_params.items():
        if key not in params:
            params[key] = value
    
    # Get word timing info
    words = word_timing if isinstance(word_timing, list) else word_timing.get("words", [])
    if not words:
        # If no word timing, return default scale
        return 1.0, (0, 0)
    
    # Find the currently active word
    active_word = None
    
    for i, word in enumerate(words):
        word_start = word.get("start", 0)
        word_end = word.get("end", word_start + 0.5)
        
        # Check if this word is active
        if word_start <= current_time <= word_end:
            active_word = word
            break
    
    # If no active word found, return default scale
    if active_word is None:
        return 1.0, (0, 0)
    
    # Calculate scale based on timing
    word_start = active_word.get("start", 0)
    word_end = active_word.get("end", word_start + 0.5)
    word_text = active_word.get("word", "").strip().lower()
    
    # Calculate progress through the word (0.0 to 1.0)
    word_duration = word_end - word_start
    progress = (current_time - word_start) / word_duration if word_duration > 0 else 0.5
    
    # Base scale calculation - start small, grow to max at middle, then shrink
    if progress < 0.5:
        # First half - grow
        scale_progress = progress * 2  # 0.0 to 1.0
        scale_factor = params["min_scale"] + (params["max_scale"] - params["min_scale"]) * scale_progress
    else:
        # Second half - shrink
        scale_progress = (1.0 - progress) * 2  # 1.0 to 0.0
        scale_factor = params["min_scale"] + (params["max_scale"] - params["min_scale"]) * scale_progress
    
    # Apply additional emphasis for keywords
    if params["emphasize_keywords"]:
        # Check if the word is a keyword
        is_keyword = any(keyword in word_text for keyword in params["keywords"])
        if is_keyword:
            scale_factor *= params["emphasis_scale"]
    
    # Calculate position offset to keep the word centered during scaling
    position_offset = (0, 0)  # No offset for now
    
    return scale_factor, position_offset

def apply_color_shift_effect(text, font, current_time, word_timing, params=None):
    """
    Apply a color shift effect based on word importance
    
    Args:
        text (str): The text to render
        font (ImageFont): The font to use
        current_time (float): Current video time in seconds
        word_timing (dict): Dictionary with word timing info
        params (dict): Optional parameters to customize the effect
        
    Returns:
        tuple: (color_rgb, None)
    """
    # Default parameters
    default_params = {
        "regular_color": (255, 255, 255),  # White
        "emphasis_color": (255, 255, 0),   # Yellow
        "strong_emphasis_color": (255, 150, 0),  # Orange
        "keywords": ["important", "key", "critical", "essential", "significant", "major"],
        "strong_keywords": ["must", "vital", "crucial", "extremely"]
    }
    
    # Use provided params or defaults
    if params is None:
        params = {}
    
    # Merge with defaults
    for key, value in default_params.items():
        if key not in params:
            params[key] = value
    
    # Get word timing info
    words = word_timing if isinstance(word_timing, list) else word_timing.get("words", [])
    if not words:
        # If no word timing, return default color
        return params["regular_color"], None
    
    # Find the currently active word
    active_word = None
    
    for i, word in enumerate(words):
        word_start = word.get("start", 0)
        word_end = word.get("end", word_start + 0.5)
        
        # Check if this word is active
        if word_start <= current_time <= word_end:
            active_word = word
            break
    
    # If no active word found, return default color
    if active_word is None:
        return params["regular_color"], None
    
    # Get the word text
    word_text = active_word.get("word", "").strip().lower()
    
    # Check if the word is a keyword
    is_strong_keyword = any(keyword in word_text for keyword in params["strong_keywords"])
    if is_strong_keyword:
        return params["strong_emphasis_color"], None
        
    is_keyword = any(keyword in word_text for keyword in params["keywords"])
    if is_keyword:
        return params["emphasis_color"], None
    
    # Default color for regular words
    return params["regular_color"], None

def apply_wave_effect(text, font, current_time, word_timing, params=None):
    """
    Apply a wave effect to text
    
    Args:
        text (str): The text to render
        font (ImageFont): The font to use
        current_time (float): Current video time in seconds
        word_timing (dict): Dictionary with word timing info
        params (dict): Optional parameters to customize the effect
        
    Returns:
        tuple: (None, position_offset_y)
    """
    # Default parameters
    default_params = {
        "amplitude": 10,  # pixels
        "frequency": 2.0  # cycles per second
    }
    
    # Use provided params or defaults
    if params is None:
        params = {}
    
    # Merge with defaults
    for key, value in default_params.items():
        if key not in params:
            params[key] = value
    
    # Calculate wave offset based on time
    wave_offset = params["amplitude"] * math.sin(current_time * 2 * math.pi * params["frequency"])
    
    return None, (0, wave_offset)

def apply_typewriter_effect(text, font, current_time, word_timing, params=None):
    """
    Apply a typewriter effect to text
    
    Args:
        text (str): The text to render
        font (ImageFont): The font to use
        current_time (float): Current video time in seconds
        word_timing (dict): Dictionary with word timing info
        params (dict): Optional parameters to customize the effect
        
    Returns:
        tuple: (visible_text, None)
    """
    # Default parameters
    default_params = {
        "chars_per_second": 15
    }
    
    # Use provided params or defaults
    if params is None:
        params = {}
    
    # Merge with defaults
    for key, value in default_params.items():
        if key not in params:
            params[key] = value
    
    # Get word timing info
    words = word_timing if isinstance(word_timing, list) else word_timing.get("words", [])
    if not words:
        # If no word timing, return full text
        return text, None
    
    # Find the currently active word
    active_word = None
    
    for i, word in enumerate(words):
        word_start = word.get("start", 0)
        word_end = word.get("end", word_start + 0.5)
        
        # Check if this word is active
        if word_start <= current_time <= word_end:
            active_word = word
            break
    
    # If no active word found, return empty text
    if active_word is None:
        return "", None
    
    # Calculate how many characters should be visible
    word_start = active_word.get("start", 0)
    word_text = active_word.get("word", "")
    
    # Time since word started
    elapsed_time = current_time - word_start
    
    # Calculate visible characters
    visible_chars = min(len(word_text), int(elapsed_time * params["chars_per_second"]))
    
    # Return visible portion of text
    return word_text[:visible_chars], None

# Handler functions for each effect
def fade_effect_handler(frame_img, text, words_with_times, current_time, style, params=None):
    """Handler for fade effect"""
    # Get opacity
    _, opacity = apply_fade_effect(text, None, current_time, words_with_times, params)
    
    # Apply opacity to the frame
    from PIL import Image
    import numpy as np
    
    # Convert to PIL Image if needed
    if isinstance(frame_img, np.ndarray):
        frame_pil = Image.fromarray(frame_img)
    else:
        frame_pil = frame_img
    
    # Ensure the image is in RGBA mode
    if frame_pil.mode != 'RGBA':
        frame_pil = frame_pil.convert('RGBA')
    
    # Apply opacity
    data = frame_pil.getdata()
    new_data = []
    for item in data:
        # Keep RGB the same, multiply A by opacity
        if len(item) == 4:  # RGBA
            new_data.append((item[0], item[1], item[2], int(item[3] * opacity)))
        else:  # RGB
            alpha = int(255 * opacity)
            new_data.append((item[0], item[1], item[2], alpha))
    
    # Create new image with updated data
    frame_pil.putdata(new_data)
    
    # Convert back to numpy array if needed
    if isinstance(frame_img, np.ndarray):
        return np.array(frame_pil)
    
    return frame_pil

def scale_effect_handler(frame_img, text, words_with_times, current_time, style, params=None):
    """Handler for scale effect"""
    # Get scale factor
    scale_factor, _ = apply_scale_effect(text, None, current_time, words_with_times, params)
    
    # Apply scaling to the frame
    from PIL import Image
    import numpy as np
    
    # Convert to PIL Image if needed
    if isinstance(frame_img, np.ndarray):
        frame_pil = Image.fromarray(frame_img)
    else:
        frame_pil = frame_img
    
    # Get original dimensions
    width, height = frame_pil.size
    
    # Calculate new dimensions
    new_width = int(width * scale_factor)
    new_height = int(height * scale_factor)
    
    # Resize the image
    resized = frame_pil.resize((new_width, new_height), Image.LANCZOS)
    
    # Create a new image with original size
    result = Image.new(frame_pil.mode, (width, height), (0, 0, 0, 0))
    
    # Paste the resized image in the center
    x_offset = (width - new_width) // 2
    y_offset = (height - new_height) // 2
    result.paste(resized, (x_offset, y_offset))
    
    # Convert back to numpy array if needed
    if isinstance(frame_img, np.ndarray):
        return np.array(result)
    
    return result

def color_shift_handler(frame_img, text, words_with_times, current_time, style, params=None):
    """Handler for color shift effect"""
    # Get color
    color, _ = apply_color_shift_effect(text, None, current_time, words_with_times, params)
    
    # Override text color in style
    if style:
        style["text_color"] = color
    
    # Return original frame (color will be applied when text is drawn)
    return frame_img

def wave_effect_handler(frame_img, text, words_with_times, current_time, style, params=None):
    """Handler for wave effect"""
    # Get wave offset
    _, (_, y_offset) = apply_wave_effect(text, None, current_time, words_with_times, params)
    
    # Apply wave offset to the frame
    from PIL import Image
    import numpy as np
    
    # Convert to PIL Image if needed
    if isinstance(frame_img, np.ndarray):
        frame_pil = Image.fromarray(frame_img)
    else:
        frame_pil = frame_img
    
    # Create a new image with the same size
    result = Image.new(frame_pil.mode, frame_pil.size, (0, 0, 0, 0))
    
    # Paste the original image with offset
    result.paste(frame_pil, (0, int(y_offset)))
    
    # Convert back to numpy array if needed
    if isinstance(frame_img, np.ndarray):
        return np.array(result)
    
    return result

def typewriter_effect_handler(frame_img, text, words_with_times, current_time, style, params=None):
    """Handler for typewriter effect"""
    # Get visible text
    visible_text, _ = apply_typewriter_effect(text, None, current_time, words_with_times, params)
    
    # We'll return the original frame, but we need to modify the text
    # This will be handled in the make_frame_with_text function
    
    # For now, just return the frame
    return frame_img, visible_text

# Map of effect names to handler functions
EFFECT_HANDLERS = {
    "fade": fade_effect_handler,
    "scale": scale_effect_handler,
    "color_shift": color_shift_handler,
    "wave": wave_effect_handler,
    "typewriter": typewriter_effect_handler
} 