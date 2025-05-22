#!/usr/bin/env python3
"""
Advanced typography effects using Pillow
This module provides more sophisticated typography effects for captions
"""

import os
import sys
import math
import random
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

def apply_kinetic_typography(img, text, font, position, color, progress, amplitude=20, frequency=2):
    """
    Apply kinetic typography effect where each word moves independently
    
    Args:
        img: Image to draw on
        text: Text to render
        font: Font to use
        position: Base position to render text
        color: Text color
        progress: Progress through the effect (0.0 to 1.0)
        amplitude: Maximum movement amplitude
        frequency: Movement frequency
    
    Returns:
        PIL.Image: Image with kinetic text
    """
    # Split text into words
    words = text.split()
    
    # Create a temporary image for the text
    text_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_img)
    
    # Calculate total width to center the text block
    total_width = 0
    word_widths = []
    
    for word in words:
        word_bbox = font.getbbox(word)
        word_width = word_bbox[2]
        word_widths.append(word_width)
        total_width += word_width + 10  # Add spacing between words
    
    # Remove extra spacing after last word
    total_width -= 10
    
    # Calculate starting x position based on alignment
    x, y = position
    
    # Determine text alignment
    text_align = getattr(img, "text_align", "center")
    
    if text_align == "left":
        start_x = x
    elif text_align == "right":
        start_x = x - total_width
    else:  # center (default)
        start_x = x - total_width // 2
    
    # Draw each word with its own movement
    current_x = start_x
    
    for i, word in enumerate(words):
        # Calculate unique movement for this word
        word_progress = (progress + i * 0.2) % 1.0  # Offset progress for each word
        
        # Calculate vertical movement (wave pattern)
        y_offset = amplitude * math.sin(word_progress * math.pi * frequency)
        
        # Calculate horizontal movement (slight jitter)
        x_offset = amplitude * 0.3 * math.cos(word_progress * math.pi * frequency * 1.5)
        
        # Calculate word opacity (pulsing effect)
        alpha = int(255 * (0.7 + 0.3 * math.sin(word_progress * math.pi * 2)))
        
        # Apply color with calculated alpha
        if len(color) == 4:
            word_color = (color[0], color[1], color[2], min(color[3], alpha))
        else:
            word_color = (*color, alpha)
        
        # Draw the word at its animated position
        draw.text((current_x + x_offset, y + y_offset), word, fill=word_color, font=font)
        
        # Move to next word position
        current_x += word_widths[i] + 10
    
    # Composite the text onto the original image
    img.paste(text_img, (0, 0), text_img)
    
    return img

def apply_audio_reactive_text(img, text, font, position, color, audio_level, base_size=1.0, max_scale=1.5):
    """
    Apply audio-reactive text effect where text size/intensity responds to audio levels
    
    Args:
        img: Image to draw on
        text: Text to render
        font: Font to use
        position: Position to render text
        color: Text color
        audio_level: Audio level (0.0 to 1.0)
        base_size: Base size multiplier
        max_scale: Maximum scale factor
    
    Returns:
        PIL.Image: Image with audio-reactive text
    """
    # Create a temporary image for the text
    text_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_img)
    
    # Get text alignment from style
    text_align = getattr(img, "text_align", "center")
    
    # Calculate scale factor based on audio level
    scale = base_size + (max_scale - base_size) * audio_level
    
    # Calculate text dimensions
    text_bbox = font.getbbox(text)
    text_width = text_bbox[2]
    text_height = text_bbox[3]
    
    # Calculate scaled font size
    scaled_font_size = int(font.size * scale)
    try:
        scaled_font = ImageFont.truetype(font.path, scaled_font_size)
    except (AttributeError, OSError):
        # Fallback if we can't get the font path
        scaled_font = font
    
    # Calculate scaled text dimensions
    scaled_text_bbox = scaled_font.getbbox(text)
    scaled_text_width = scaled_text_bbox[2]
    
    # Calculate position adjustments to keep text centered or aligned
    x, y = position
    
    if text_align == "left":
        x_adjust = 0
    elif text_align == "right":
        x_adjust = scaled_text_width - text_width
    else:  # center (default)
        x_adjust = (scaled_text_width - text_width) // 2
    
    y_adjust = (text_height * scale - text_height) // 2
    
    # Draw the text with scaled font
    draw.text((x - x_adjust, y - y_adjust), text, fill=color, font=scaled_font)
    
    # Add glow effect based on audio level
    if audio_level > 0.5:
        glow_intensity = (audio_level - 0.5) * 2  # 0.0 to 1.0
        glow_img = text_img.copy()
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=3 * glow_intensity))
        
        # Enhance the glow
        enhancer = ImageEnhance.Brightness(glow_img)
        glow_img = enhancer.enhance(1.5)
        
        # Composite the glow behind the text
        text_img = Image.alpha_composite(glow_img, text_img)
    
    # Composite the text onto the original image
    img.paste(text_img, (0, 0), text_img)
    
    return img

def apply_character_animation(img, text, font, position, color, progress, effect_type="typewriter"):
    """
    Apply character-by-character animation effects
    
    Args:
        img: Image to draw on
        text: Text to render
        font: Font to use
        position: Position to render text
        color: Text color
        progress: Progress through the effect (0.0 to 1.0)
        effect_type: Type of character animation ("typewriter", "fade_in", "drop_in", "spin_in")
    
    Returns:
        PIL.Image: Image with character animation
    """
    # Create a temporary image for the text
    text_img = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(text_img)
    
    # Get text alignment from style
    text_align = getattr(img, "text_align", "center")
    
    # Calculate total width to center the text block
    text_bbox = font.getbbox(text)
    text_width = text_bbox[2]
    
    # Calculate starting x position based on alignment
    x, y = position
    
    if text_align == "left":
        start_x = x
    elif text_align == "right":
        start_x = x - text_width
    else:  # center (default)
        start_x = x - text_width // 2
    
    # Calculate how many characters to show based on progress
    char_count = len(text)
    visible_chars = min(char_count, int(char_count * progress * 1.2))
    
    # Track current position
    current_x = start_x
    
    # Process each character
    for i, char in enumerate(text):
        # Skip if beyond visible characters
        if i >= visible_chars and effect_type == "typewriter":
            continue
            
        # Calculate character width
        char_bbox = font.getbbox(char)
        char_width = char_bbox[2]
        
        # Calculate character-specific progress
        char_progress = min(1.0, max(0.0, (progress * char_count - i) / 1.0))
        
        # Apply different effects based on type
        if effect_type == "fade_in":
            # Fade in each character
            opacity = int(255 * char_progress)
            char_color = (*color[:3], opacity) if len(color) >= 3 else (*color, opacity)
            draw.text((current_x, y), char, fill=char_color, font=font)
            
        elif effect_type == "drop_in":
            # Drop in from above
            if char_progress < 1.0:
                drop_y = y - (1.0 - char_progress) * 50
                draw.text((current_x, drop_y), char, fill=color, font=font)
            else:
                draw.text((current_x, y), char, fill=color, font=font)
                
        elif effect_type == "spin_in":
            # Create a temporary image for this character
            char_img = Image.new('RGBA', (char_width * 2, int(font.size * 2)), (0, 0, 0, 0))
            char_draw = ImageDraw.Draw(char_img)
            
            # Draw character centered in the temp image
            char_draw.text((char_width // 2, font.size // 2), char, fill=color, font=font, anchor="mm")
            
            # Rotate based on progress
            if char_progress < 1.0:
                rotation = (1.0 - char_progress) * 360
                char_img = char_img.rotate(rotation, resample=Image.BICUBIC, expand=True, center=(char_width // 2, font.size // 2))
                
                # Scale based on progress
                scale = 0.5 + 0.5 * char_progress
                new_size = (int(char_img.width * scale), int(char_img.height * scale))
                char_img = char_img.resize(new_size, Image.LANCZOS)
            
            # Paste character onto text image
            text_img.paste(char_img, (current_x - char_width // 2, y - font.size // 2), char_img)
            
        else:  # typewriter or default
            draw.text((current_x, y), char, fill=color, font=font)
        
        # Move to next character position
        current_x += char_width
    
    # Composite the text onto the original image
    img.paste(text_img, (0, 0), text_img)
    
    return img

def make_frame_with_advanced_typography(frame, text, font_path, font_size, current_time, word_timing, 
                                       effects=None, style=None, audio_data=None):
    """
    Add captions with advanced typography effects to a video frame
    
    Args:
        frame: Video frame (numpy array)
        text: Text to render
        font_path: Path to font file
        font_size: Font size
        current_time: Current time in seconds
        word_timing: Word timing information
        effects: List of effects to apply
        style: Style parameters
        audio_data: Audio level data for audio-reactive effects
    
    Returns:
        numpy.ndarray: Frame with captions
    """
    # Convert frame to PIL Image
    frame_pil = Image.fromarray(frame)
    
    # Default effects if none provided
    if effects is None:
        effects = []
    
    # Default style if none provided
    if style is None:
        style = {
            "text_color": (255, 255, 255, 255),
            "highlight_color": None,
            "highlight_padding": 15,
            "position": "bottom",
            "shadow": True,
            "word_by_word": True
        }
    
    # Load font
    try:
        font = ImageFont.truetype(font_path, font_size)
    except:
        # Fallback to default font
        font = ImageFont.load_default()
        font_size = 24
    
    # Calculate text position based on style
    width, height = frame_pil.size
    
    # Calculate text dimensions
    text_bbox = font.getbbox(text)
    text_width = text_bbox[2]
    text_height = text_bbox[3]
    
    # Get maximum width constraint from style (default to 80% if not specified)
    max_width_percent = style.get("max_width_percent", 80)
    max_text_width = int(width * max_width_percent / 100)
    
    # If text is wider than allowed, scale it down
    if text_width > max_text_width:
        scale_factor = max_text_width / text_width
        new_font_size = int(font_size * scale_factor)
        try:
            font = ImageFont.truetype(font_path, new_font_size)
            # Recalculate text dimensions with new font size
            text_bbox = font.getbbox(text)
            text_width = text_bbox[2]
            text_height = text_bbox[3]
        except:
            # If font scaling fails, we'll just use original dimensions
            print(f"Warning: Failed to scale font to fit max width. Text may be cut off.")
    
    # Get position from style
    position = style.get("position", "bottom")
    
    # Extended position handling
    if position == "bottom":
        text_x = width // 2
        text_y = height - text_height - style["highlight_padding"] * 2
    elif position == "top":
        text_x = width // 2
        text_y = style["highlight_padding"]
    elif position == "center":
        text_x = width // 2
        text_y = height // 2
    elif position == "bottom_left" or position == "bottom-left":
        text_x = style["highlight_padding"] + text_width // 2
        text_y = height - text_height - style["highlight_padding"] * 2
    elif position == "bottom_right" or position == "bottom-right":
        text_x = width - text_width // 2 - style["highlight_padding"]
        text_y = height - text_height - style["highlight_padding"] * 2
    elif position == "top_left" or position == "top-left":
        text_x = style["highlight_padding"] + text_width // 2
        text_y = style["highlight_padding"]
    elif position == "top_right" or position == "top-right":
        text_x = width - text_width // 2 - style["highlight_padding"]
        text_y = style["highlight_padding"]
    elif position == "custom" and "custom_x" in style and "custom_y" in style:
        # Use the exact custom position coordinates
        custom_x_percent = style["custom_x"]
        custom_y_percent = style["custom_y"]
        
        # Convert percentages to pixel coordinates
        text_x = int(width * custom_x_percent / 100)
        text_y = int(height * custom_y_percent / 100)
        
        # Adjust for text centering if needed
        if style.get("text_align", "center") == "center":
            pass  # text_x is already the center point
        elif style.get("text_align", "center") == "left":
            text_x += text_width // 2  # Adjust because we'll center the text at text_x
        elif style.get("text_align", "center") == "right":
            text_x -= text_width // 2
            
        print(f"Using custom position: {custom_x_percent}% x {custom_y_percent}% → ({text_x}, {text_y}) px")
    else:
        # Default to bottom if unknown position
        text_x = width // 2
        text_y = height - text_height - style["highlight_padding"]
    
    # Add background if specified
    if style["highlight_color"]:
        bg_color = style["highlight_color"]
        bg_padding = style["highlight_padding"]
        
        # Create a temporary image for the background
        bg_img = Image.new('RGBA', frame_pil.size, (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg_img)
        
        bg_rect = [
            text_x - text_width // 2 - bg_padding,
            text_y - bg_padding,
            text_x + text_width // 2 + bg_padding,
            text_y + text_height + bg_padding
        ]
        bg_draw.rectangle(bg_rect, fill=bg_color)
        
        # Composite the background onto the frame
        frame_pil.paste(bg_img, (0, 0), bg_img)
    
    # Add shadow if specified
    if style["shadow"]:
        shadow_color = (0, 0, 0, 128)
        shadow_offset = 2
        
        # Create a temporary image for the shadow
        shadow_img = Image.new('RGBA', frame_pil.size, (0, 0, 0, 0))
        
        # Apply shadow based on selected effect
        if "kinetic_typography" in effects:
            shadow_img = apply_kinetic_typography(
                shadow_img, text, font, (text_x + shadow_offset, text_y + shadow_offset), 
                shadow_color, current_time % 1.0
            )
        elif "audio_reactive" in effects and audio_data is not None:
            shadow_img = apply_audio_reactive_text(
                shadow_img, text, font, (text_x + shadow_offset, text_y + shadow_offset), 
                shadow_color, audio_data
            )
        elif "character_animation" in effects:
            shadow_img = apply_character_animation(
                shadow_img, text, font, (text_x + shadow_offset, text_y + shadow_offset), 
                shadow_color, current_time % 1.0, "fade_in"
            )
        
        # Composite the shadow onto the frame
        frame_pil.paste(shadow_img, (0, 0), shadow_img)
    
    # Apply selected effects
    if "kinetic_typography" in effects:
        # Set text alignment attribute on the image for the effect function to use
        frame_pil.text_align = style.get("text_align", "center")
        
        frame_pil = apply_kinetic_typography(
            frame_pil, text, font, (text_x, text_y), 
            style["text_color"], current_time % 1.0
        )
    elif "audio_reactive" in effects:
        # Use a simulated audio level if real data not provided
        audio_level = 0.5 + 0.5 * math.sin(current_time * math.pi) if audio_data is None else audio_data
        
        # Set text alignment attribute on the image for the effect function to use
        frame_pil.text_align = style.get("text_align", "center")
        
        frame_pil = apply_audio_reactive_text(
            frame_pil, text, font, (text_x, text_y), 
            style["text_color"], audio_level
        )
    elif "character_animation" in effects:
        # Choose a character animation effect based on text content or style
        effect_type = "typewriter"
        if "character_effect" in style:
            effect_type = style["character_effect"]
        
        # Set text alignment attribute on the image for the effect function to use
        frame_pil.text_align = style.get("text_align", "center")
        
        frame_pil = apply_character_animation(
            frame_pil, text, font, (text_x, text_y), 
            style["text_color"], current_time % 1.0, effect_type
        )
    
    # Convert back to numpy array
    return np.array(frame_pil)

# Example usage
if __name__ == "__main__":
    # Create test image
    width, height = 1280, 720
    test_image = Image.new('RGB', (width, height), (20, 20, 20))
    
    # Test text
    text = "This is advanced typography!"
    
    # Default TikTok style
    style = {
        "text_color": (255, 255, 255, 255),
        "highlight_color": (0, 0, 0, 200),
        "highlight_padding": 15,
        "position": "bottom",
        "shadow": True,
        "word_by_word": True
    }
    
    # Test each effect
    effects_to_test = [
        ["kinetic_typography"],
        ["audio_reactive"],
        ["character_animation"]
    ]
    
    for effects in effects_to_test:
        effect_name = effects[0]
        print(f"Testing {effect_name} effect...")
        
        for t in [0.2, 0.4, 0.6, 0.8, 1.0]:
            # Create a copy of the test image
            test_frame = test_image.copy()
            
            # For audio_reactive, simulate different audio levels
            audio_level = None
            if effect_name == "audio_reactive":
                audio_level = t
            
            # Add caption with effect
            captioned_frame = make_frame_with_advanced_typography(
                frame=np.array(test_frame),
                text=text,
                font_path="Arial.ttf",  # Use a system font
                font_size=42,
                current_time=t,
                word_timing=None,
                effects=effects,
                style=style,
                audio_data=audio_level
            )
            
            # Save the frame
            output_dir = f"advanced_typography_test/{effect_name}"
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"{effect_name}_test_{t:.1f}.png")
            
            # Convert back to PIL and save
            Image.fromarray(captioned_frame).save(output_path)
            
            print(f"  Saved {effect_name} test at time {t:.1f}s to: {output_path}")
    
    print("Advanced typography effects tests complete!") 