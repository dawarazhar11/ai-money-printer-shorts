#!/usr/bin/env python3
"""
Demonstration of combining multiple typography effects
"""

import os
import sys
from pathlib import Path

# Add the parent directory to sys.path
app_dir = Path(__file__).parent.absolute()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
    print(f"Added {app_dir} to path")

try:
    from PIL import Image, ImageDraw, ImageFont
    from typography_effects_fade import apply_fade_effect, apply_fade_to_image
    from typography_effects_scale import apply_scale_effect
    print("Successfully imported modules")
except ImportError as e:
    print(f"Error importing modules: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

def render_word_with_combined_effects(draw, word, position, font, color, current_time, word_timing, params=None):
    """
    Render a word with combined fade and scale effects
    
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
    # Get default parameters
    if params is None:
        params = {}
    
    # Extract effect-specific parameters
    fade_params = params.get("fade", {})
    scale_params = params.get("scale", {})
    
    # Calculate fade effect
    _, opacity = apply_fade_effect(word, font, current_time, word_timing, fade_params)
    
    # Calculate scale effect
    scale_factor, (offset_x, offset_y) = apply_scale_effect(word, font, current_time, word_timing, scale_params)
    
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
    
    # Apply opacity to color
    if len(color) == 3:  # RGB
        color_with_opacity = (*color, int(255 * opacity))
    else:  # RGBA
        color_with_opacity = (*color[:3], int(color[3] * opacity))
    
    # Draw the text with the scaled font and opacity
    draw.text((new_x, new_y), word, fill=color_with_opacity, font=scaled_font)
    
    # Return the original text size (not the scaled size)
    # This ensures proper spacing between words
    return text_width, text_height

def render_text_with_combined_effects(text, font, current_time, word_timing, params=None):
    """
    Render text with combined fade and scale effects for each word
    
    Args:
        text (str): Text to render
        font (PIL.ImageFont): Font to use
        current_time (float): Current video time in seconds
        word_timing (dict): Word timing information
        params (dict): Effect parameters
        
    Returns:
        PIL.Image: Rendered text with combined effects
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
    
    # Render each word with combined effects
    for word in words:
        word_width, word_height = render_word_with_combined_effects(
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

def test_combined_effects():
    """Test the combined effects with sample text and timing"""
    from PIL import ImageFont
    import time
    
    # Create a sample font
    try:
        font = ImageFont.truetype("Arial.ttf", 36)
    except OSError:
        # Try to find a system font
        try:
            if sys.platform == "darwin":  # macOS
                font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 36)
            elif sys.platform == "win32":  # Windows
                font = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 36)
            else:  # Linux and others
                font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except OSError:
            # Last resort - use default font
            font = ImageFont.load_default()
            print("Warning: Using default font")
    
    # Sample word timing
    word_timing = {
        "words": [
            {"word": "This", "start": 0.0, "end": 0.5},
            {"word": "is", "start": 0.5, "end": 0.8},
            {"word": "a", "start": 0.8, "end": 1.0},
            {"word": "combined", "start": 1.0, "end": 1.5},
            {"word": "effect", "start": 1.5, "end": 2.0},
            {"word": "important", "start": 2.0, "end": 2.5},
            {"word": "test", "start": 2.5, "end": 3.0}
        ]
    }
    
    # Combined effect parameters
    params = {
        "fade": {
            "fade_in_duration": 0.2,
            "fade_out_duration": 0.1,
            "min_opacity": 0.2,
            "max_opacity": 1.0
        },
        "scale": {
            "min_scale": 0.8,
            "max_scale": 1.5,
            "emphasize_keywords": True,
            "keywords": ["important", "combined"]
        }
    }
    
    # Test at different time points
    test_times = [0.1, 0.4, 0.6, 0.9, 1.2, 1.7, 2.2, 2.7]
    
    # Create output directory
    os.makedirs("effect_samples", exist_ok=True)
    
    for t in test_times:
        # Render text with combined effects
        text_image = render_text_with_combined_effects(
            "This is a combined effect important test",
            font, t, word_timing, params
        )
        
        # Save the image
        output_path = f"effect_samples/combined_effects_{t:.1f}.png"
        text_image.save(output_path)
        print(f"Rendered combined effects at time {t:.1f}s - saved to {output_path}")

def create_integration_example():
    """Create an example of how to integrate these effects into the captions module"""
    print("\nExample of integrating combined effects into captions module:")
    
    code_example = '''
    # Add this to utils/video/captions.py
    
    def apply_typography_effects(frame_img, text, words_with_times, current_time, style):
        """Apply typography effects to the frame"""
        if not "typography_effects" in style or not style["typography_effects"]:
            return frame_img
            
        # Get the effects to apply
        effects = style["typography_effects"]
        
        # Apply each effect in sequence
        for effect_name in effects:
            if effect_name == "fade":
                # Apply fade effect
                params = TYPOGRAPHY_EFFECTS["fade"]["params"]
                _, opacity = apply_fade_effect(text, font, current_time, words_with_times, params)
                # Apply opacity to text
                # ...
            
            elif effect_name == "scale":
                # Apply scale effect
                params = TYPOGRAPHY_EFFECTS["scale"]["params"]
                scale_factor, offset = apply_scale_effect(text, font, current_time, words_with_times, params)
                # Apply scaling to text
                # ...
                
            # Add other effects as needed
                
        return frame_img
    
    # Then in make_frame_with_text, add:
    frame_img = apply_typography_effects(frame_img, text, words_with_times, current_time, style)
    '''
    
    print(code_example)

def main():
    """Main function"""
    print("Typography Effects Combination Demo")
    print("==================================\n")
    
    # Test combined effects
    test_combined_effects()
    
    # Show integration example
    create_integration_example()
    
    print("\nNext steps:")
    print("1. Integrate these effect handlers into the captions module")
    print("2. Add UI controls in the Streamlit app to customize effects")
    print("3. Create more effects (wave, color_shift, typewriter)")
    print("4. Optimize performance for real-time rendering")

if __name__ == "__main__":
    main() 