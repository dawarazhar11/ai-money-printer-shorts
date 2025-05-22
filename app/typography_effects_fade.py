#!/usr/bin/env python3
"""
Implementation of the Fade typography effect for captions
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
        tuple: (text_image, alpha_mask)
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
    words = word_timing.get("words", [])
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

def apply_fade_to_image(image, opacity):
    """
    Apply opacity to an image
    
    Args:
        image (PIL.Image): The image to apply opacity to
        opacity (float): Opacity value from 0.0 to 1.0
        
    Returns:
        PIL.Image: Image with applied opacity
    """
    if image is None:
        return None
        
    # Ensure image is in RGBA mode
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Get image data
    data = image.getdata()
    new_data = []
    
    # Apply opacity to each pixel
    for item in data:
        # Keep RGB the same, multiply A by opacity
        if len(item) == 4:  # RGBA
            new_data.append((item[0], item[1], item[2], int(item[3] * opacity)))
        else:  # RGB
            alpha = int(255 * opacity)
            new_data.append((item[0], item[1], item[2], alpha))
    
    # Create new image with updated data
    image.putdata(new_data)
    return image

def render_word_with_fade(draw, word, position, font, color, current_time, word_timing, params=None):
    """
    Render a word with fade effect
    
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
    # Calculate fade effect
    _, opacity = apply_fade_effect(word, font, current_time, word_timing, params)
    
    # Adjust color with opacity
    if len(color) == 3:  # RGB
        color_with_opacity = (*color, int(255 * opacity))
    else:  # RGBA
        color_with_opacity = (*color[:3], int(color[3] * opacity))
    
    # Draw the text
    draw.text(position, word, fill=color_with_opacity, font=font)
    
    # Calculate and return text size
    try:
        # Try newer Pillow 10.0+ method first
        text_bbox = draw.textbbox(position, word, font=font)
        return (text_bbox[2] - text_bbox[0], text_bbox[3] - text_bbox[1])
    except (AttributeError, TypeError):
        try:
            # Fall back to older method
            return draw.textsize(word, font=font)
        except (AttributeError, TypeError):
            # Last resort fallback - estimate based on font size
            return (len(word) * font.size * 0.6, font.size * 1.2)

def render_text_with_fade_effect(text, font, current_time, word_timing, params=None):
    """
    Render text with fade effect for each word
    
    Args:
        text (str): Text to render
        font (PIL.ImageFont): Font to use
        current_time (float): Current video time in seconds
        word_timing (dict): Word timing information
        params (dict): Effect parameters
        
    Returns:
        PIL.Image: Rendered text with fade effect
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
    
    # Render each word with fade effect
    for word in words:
        word_width, word_height = render_word_with_fade(
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
def test_fade_effect():
    """Test the fade effect with sample text and timing"""
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
            {"word": "fade", "start": 1.0, "end": 1.5},
            {"word": "effect", "start": 1.5, "end": 2.0},
            {"word": "test", "start": 2.0, "end": 2.5}
        ]
    }
    
    # Test at different time points
    test_times = [0.1, 0.4, 0.6, 0.9, 1.2, 1.7, 2.2, 2.4, 2.6]
    
    for t in test_times:
        # Render text with fade effect
        text_image = render_text_with_fade_effect(
            "This is a fade effect test",
            font, t, word_timing
        )
        
        # Save the image
        text_image.save(f"fade_effect_test_{t:.1f}.png")
        print(f"Rendered fade effect at time {t:.1f}s")

if __name__ == "__main__":
    test_fade_effect() 