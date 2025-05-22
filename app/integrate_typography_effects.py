#!/usr/bin/env python3
"""
Script to integrate typography effects with the captions module
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
    from utils.video.captions import (
        check_dependencies,
        add_captions_to_video,
        CAPTION_STYLES,
        TYPOGRAPHY_EFFECTS
    )
    from typography_effects_fade import apply_fade_effect, apply_fade_to_image
    print("Successfully imported modules")
except ImportError as e:
    print(f"Error importing modules: {e}")
    import traceback
    print(traceback.format_exc())
    sys.exit(1)

def integrate_fade_effect():
    """
    Show how to integrate the fade effect into the captions module
    """
    # Step 1: Define the function that will be called by the captions module
    def fade_effect_handler(frame_img, text, words_with_times, current_time, style, effect_params=None):
        """
        Handler function for the fade effect that matches the signature expected by captions module
        
        Args:
            frame_img: The video frame as numpy array or PIL Image
            text: The text to render
            words_with_times: Dictionary with word timing info
            current_time: Current video time in seconds
            style: Caption style dictionary
            effect_params: Optional parameters for the effect
            
        Returns:
            Modified frame with the effect applied
        """
        # This is where we would integrate with the existing captions module
        # For now, we'll just print what would happen
        print(f"Applying fade effect at time {current_time:.2f}s for text: {text}")
        
        # In a real implementation, we would:
        # 1. Get the opacity for each word based on timing
        # 2. Render the text with varying opacity
        # 3. Composite the result onto the frame
        
        # For demonstration, we'll just return the original frame
        return frame_img
    
    # Step 2: Register the effect handler in the TYPOGRAPHY_EFFECTS dictionary
    # This is how we would add our effect to the existing captions module
    print("Registering fade effect handler...")
    
    # Define the effect parameters
    fade_effect = {
        "description": "Fade in/out effect for each word",
        "params": {
            "fade_in_duration": 0.2,
            "fade_out_duration": 0.1,
            "min_opacity": 0.0,
            "max_opacity": 1.0,
            "fade_between_words": True
        },
        "handler": fade_effect_handler
    }
    
    # Register the effect (in a real implementation)
    print("In a real implementation, we would add this to TYPOGRAPHY_EFFECTS['fade']")
    
    # Step 3: Show how to use the effect in a caption style
    print("\nExample of using the fade effect in a caption style:")
    
    # Create a custom style with the fade effect
    custom_style = {
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
        "typography_effects": ["fade"]  # Use the fade effect
    }
    
    print("Custom style with fade effect:")
    print(custom_style)
    
    # Step 4: Show how to apply the custom style to a video
    print("\nTo apply this to a video, you would use:")
    print("""
    result = add_captions_to_video(
        video_path="your_video.mp4",
        output_path="output_with_fade.mp4",
        style_name="tiktok",  # Base style
        custom_style=custom_style  # Override with our custom style
    )
    """)

def modify_captions_module():
    """
    Show the changes needed in the captions module to support typography effects
    """
    print("\nChanges needed in the captions module:")
    
    print("""
    1. In the make_frame_with_text function:
    
    def make_frame_with_text(frame_img, text, words_with_times, current_time, style, effect_params=None):
        # ... existing code ...
        
        # Apply typography effects if specified
        if "typography_effects" in style and style["typography_effects"]:
            for effect_name in style["typography_effects"]:
                if effect_name in TYPOGRAPHY_EFFECTS and "handler" in TYPOGRAPHY_EFFECTS[effect_name]:
                    # Get effect parameters
                    params = TYPOGRAPHY_EFFECTS[effect_name].get("params", {})
                    if effect_params and effect_name in effect_params:
                        # Override with custom parameters if provided
                        params.update(effect_params[effect_name])
                    
                    # Call the effect handler
                    frame_img = TYPOGRAPHY_EFFECTS[effect_name]["handler"](
                        frame_img, text, words_with_times, current_time, style, params
                    )
        
        # ... rest of the function ...
    """)
    
    print("""
    2. Update the TYPOGRAPHY_EFFECTS dictionary to include handlers:
    
    TYPOGRAPHY_EFFECTS = {
        "fade": {
            "description": "Fade in/out effect for each word",
            "params": {
                "fade_in_duration": 0.2,
                "fade_out_duration": 0.1,
                "min_opacity": 0.0,
                "max_opacity": 1.0,
                "fade_between_words": True
            },
            "handler": fade_effect_handler  # Add the handler function
        },
        # ... other effects ...
    }
    """)

def main():
    """Main function"""
    print("Typography Effects Integration Demo")
    print("==================================\n")
    
    # Show how to integrate the fade effect
    integrate_fade_effect()
    
    # Show the changes needed in the captions module
    modify_captions_module()
    
    print("\nNext steps:")
    print("1. Implement the fade_effect_handler function in the captions module")
    print("2. Add similar handlers for other effects (scale, color_shift, wave, typewriter)")
    print("3. Update the make_frame_with_text function to apply the effects")
    print("4. Test each effect individually and in combination")
    print("5. Add UI controls in the Streamlit app to customize effects")

if __name__ == "__main__":
    main() 