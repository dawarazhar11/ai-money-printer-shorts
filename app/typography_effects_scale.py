#!/usr/bin/env python3
"""
Implementation of the Scale typography effect for captions
"""

import math
from PIL import Image, ImageDraw, ImageFont

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
    words = word_timing.get("words", [])
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
    # This is a simplification - in a real implementation, you'd calculate based on text size
    position_offset = (0, 0)  # No offset for now
    
    return scale_factor, position_offset

def render_word_with_scale(draw, word, position, font, color, current_time, word_timing, params=None):
    """
    Render a word with scale effect
    
    Args:
        draw (PIL.ImageDraw): ImageDraw object to draw on
        word (str): Word to render
        position (tuple): (x, y) position to render at
        font (PIL.ImageFont): Font to use
        color (tuple): Color to use (RGB or RGBA)
        current_time (float): Current video time in seconds
        word_timing (dict): Word timing information
        params (dict): Effect parameters
        
    Returns:
        tuple: (width, height) of rendered text
    """
    # Calculate scale effect
    scale_factor, (offset_x, offset_y) = apply_scale_effect(word, font, current_time, word_timing, params)
    
    # Calculate original text size
    try:
        # Try newer Pillow 10.0+ method first
        text_bbox = draw.textbbox(position, word, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
    except (AttributeError, TypeError):
        try:
            # Fall back to older method
            text_width, text_height = draw.textsize(word, font=font)
        except (AttributeError, TypeError):
            # Last resort fallback - estimate based on font size
            text_width = len(word) * font.size * 0.6
            text_height = font.size * 1.2
    
    # Create a scaled font
    scaled_font_size = int(font.size * scale_factor)
    try:
        scaled_font = ImageFont.truetype(font.path, scaled_font_size)
    except (AttributeError, OSError):
        # Fallback if we can't create a scaled font
        scaled_font = font
        print(f"Warning: Could not create scaled font with size {scaled_font_size}")
    
    # Calculate new position to keep the text centered
    x, y = position
    
    # Calculate scaled text size
    try:
        # Try newer Pillow 10.0+ method first
        scaled_text_bbox = draw.textbbox((0, 0), word, font=scaled_font)
        scaled_width = scaled_text_bbox[2] - scaled_text_bbox[0]
        scaled_height = scaled_text_bbox[3] - scaled_text_bbox[1]
    except (AttributeError, TypeError):
        try:
            # Fall back to older method
            scaled_width, scaled_height = draw.textsize(word, font=scaled_font)
        except (AttributeError, TypeError):
            # Last resort fallback - estimate based on font size
            scaled_width = len(word) * scaled_font_size * 0.6
            scaled_height = scaled_font_size * 1.2
    
    # Center the scaled text
    x_offset = (text_width - scaled_width) / 2
    y_offset = (text_height - scaled_height) / 2
    
    new_x = x + x_offset + offset_x
    new_y = y + y_offset + offset_y
    
    # Draw the text with the scaled font
    draw.text((new_x, new_y), word, fill=color, font=scaled_font)
    
    # Return the original text size (not the scaled size)
    # This ensures proper spacing between words
    return text_width, text_height

def render_text_with_scale_effect(text, font, current_time, word_timing, params=None):
    """
    Render text with scale effect for each word
    
    Args:
        text (str): Text to render
        font (PIL.ImageFont): Font to use
        current_time (float): Current video time in seconds
        word_timing (dict): Word timing information
        params (dict): Effect parameters
        
    Returns:
        PIL.Image: Rendered text with scale effect
    """
    # Create a transparent image for the text
    # Start with a reasonable size, we'll crop it later
    width, height = 1000, 200
    text_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_image)
    
    # Split text into words
    words = text.split()
    
    # Start position
    x, y = 10, 10
    max_height = 0
    
    # Render each word with scale effect
    for word in words:
        word_width, word_height = render_word_with_scale(
            draw, word, (x, y), font, (255, 255, 255, 255),
            current_time, word_timing, params
        )
        
        # Update position for next word
        x += word_width + font.size * 0.2  # Add space between words
        max_height = max(max_height, word_height)
        
        # If we're near the edge, wrap to next line
        if x > width - 100:
            x = 10
            y += max_height + 5
            max_height = 0
    
    # Crop the image to the actual text size
    bbox = text_image.getbbox()
    if bbox:
        text_image = text_image.crop(bbox)
    
    return text_image

# Example usage in a test function
def test_scale_effect():
    """Test the scale effect with sample text and timing"""
    from PIL import ImageFont
    import time
    
    # Create a sample font
    font = ImageFont.truetype("Arial.ttf", 36)
    
    # Sample word timing
    word_timing = {
        "words": [
            {"word": "This", "start": 0.0, "end": 0.5},
            {"word": "is", "start": 0.5, "end": 0.8},
            {"word": "a", "start": 0.8, "end": 1.0},
            {"word": "scale", "start": 1.0, "end": 1.5},
            {"word": "effect", "start": 1.5, "end": 2.0},
            {"word": "important", "start": 2.0, "end": 2.5},
            {"word": "test", "start": 2.5, "end": 3.0}
        ]
    }
    
    # Test at different time points
    test_times = [0.1, 0.4, 0.6, 0.9, 1.2, 1.7, 2.2, 2.7]
    
    for t in test_times:
        # Render text with scale effect
        text_image = render_text_with_scale_effect(
            "This is a scale effect important test",
            font, t, word_timing
        )
        
        # Save the image
        text_image.save(f"scale_effect_test_{t:.1f}.png")
        print(f"Rendered scale effect at time {t:.1f}s")

if __name__ == "__main__":
    test_scale_effect() 