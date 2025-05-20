#!/usr/bin/env python3
"""
Page for adding modern autocaptions to videos
"""
import os
import sys
import time
import json
import traceback
from pathlib import Path
import streamlit as st

# Add the parent directory to sys.path
app_dir = Path(__file__).parent.parent.absolute()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
    print(f"Added {app_dir} to path")

try:
    from components.progress import render_step_header
    from utils.session_state import mark_step_complete
    from components.navigation import render_workflow_navigation, render_step_navigation
    from utils.video.captions import (
        check_dependencies, 
        add_captions_to_video, 
        get_available_caption_styles,
        CAPTION_STYLES
    )
    print("Successfully imported local modules")
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.info("Please make sure you're running this from the project root directory.")
    st.stop()

# Set page config
st.set_page_config(
    page_title="Autocaptions - AI Money Printer Shorts",
    page_icon="🎬",
    layout="wide"
)

# Initialize session state for this page
if "autocaptions" not in st.session_state:
    st.session_state.autocaptions = {
        "status": "not_started",
        "source_video": None,
        "output_path": None,
        "selected_style": "tiktok",
        "model_size": "base",
        "error": None
    }

# Get available caption styles
def get_available_caption_styles():
    """Get available caption styles from the captions module"""
    try:
        from utils.video.captions import CAPTION_STYLES
        return CAPTION_STYLES
    except ImportError:
        return {
            "tiktok": "TikTok Style",
            "modern_bold": "Modern Bold",
            "minimal": "Minimal",
            "news": "News Style",
            "social": "Social Media"
        }

# Get available typography effects 
def get_available_typography_effects():
    """Get available typography effects from the captions module"""
    try:
        from utils.video.captions import TYPOGRAPHY_EFFECTS
        return TYPOGRAPHY_EFFECTS
    except ImportError:
        return {
            "fade": {"description": "Fade in/out effect for each word"},
            "scale": {"description": "Scale words up/down for emphasis"},
            "color_shift": {"description": "Shift colors based on word importance"},
            "wave": {"description": "Words move in a wave pattern"},
            "typewriter": {"description": "Words appear one character at a time"}
        }

# Get available transcription engines
def get_available_transcription_engines():
    """Get available transcription engines"""
    engines = ["auto"]
    
    try:
        from utils.audio.transcription import check_module_availability
        
        # Check whisper
        if check_module_availability("whisper"):
            engines.append("whisper")
        
        # Check faster-whisper
        if check_module_availability("faster_whisper"):
            engines.append("faster_whisper")
        
        # Check vosk
        if check_module_availability("vosk"):
            engines.append("vosk")
            
    except ImportError:
        # Fallback - just check whisper directly
        try:
            import whisper
            engines.append("whisper")
        except ImportError:
            pass
        
        # Try to check for faster-whisper
        try:
            import faster_whisper
            engines.append("faster_whisper")
        except ImportError:
            pass
    
    return engines

# Main function
def main():
    # Header and navigation
    render_step_header("Autocaptions", "Add modern, appealing captions to your video")
    render_workflow_navigation()
    
    # Introduction
    st.markdown("""
    # 🎬 Autocaptions Generator
    
    Add modern, engaging captions to your videos that sync perfectly with the audio. 
    Choose from different presets to achieve the style that fits your content best!
    """)
    
    # Display the video selection panel
    st.markdown("## Step 1: Select the Video")
    
    # Option to use the previously assembled video or upload a custom one
    video_source = st.radio(
        "Video Source:",
        ["Use Assembled Video", "Upload Custom Video"],
        key="video_source"
    )
    
    if video_source == "Use Assembled Video":
        # Check for assembled video from previous step
        if "video_assembly" in st.session_state and st.session_state.video_assembly.get("output_path"):
            assembled_video_path = st.session_state.video_assembly["output_path"]
            if os.path.exists(assembled_video_path):
                st.session_state.autocaptions["source_video"] = assembled_video_path
                st.success(f"Using assembled video: {os.path.basename(assembled_video_path)}")
                
                # Display the video
                st.video(assembled_video_path)
            else:
                st.error("The assembled video file no longer exists. Please choose another option.")
                st.session_state.autocaptions["source_video"] = None
        else:
            st.warning("No assembled video found. Please go to the Video Assembly page first or upload a custom video.")
            st.session_state.autocaptions["source_video"] = None
    else:
        # Upload custom video
        uploaded_file = st.file_uploader("Upload your video file:", type=["mp4", "mov", "avi", "mkv"])
        if uploaded_file:
            # Save the uploaded file to a temporary location
            os.makedirs("output", exist_ok=True)
            temp_path = os.path.join("output", f"uploaded_{int(time.time())}.mp4")
            
            try:
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Verify the file was written successfully
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    st.session_state.autocaptions["source_video"] = temp_path
                    st.success(f"Video uploaded successfully: {os.path.basename(temp_path)}")
                    
                    # Display the video
                    st.video(temp_path)
                else:
                    st.error("Failed to save uploaded video. The file may be empty or corrupted.")
            except Exception as e:
                st.error(f"Error saving uploaded video: {str(e)}")
                st.session_state.autocaptions["source_video"] = None
    
    # Display the caption style selection
    if st.session_state.autocaptions["source_video"]:
        st.markdown("## Step 2: Choose Caption Style")
        
        # Get available styles
        styles = get_available_caption_styles()
        
        # Get available effects
        typography_effects = get_available_typography_effects()
        
        # Create columns for style selection
        col1, col2 = st.columns(2)
        
        with col1:
            # Style selection dropdown
            selected_style = st.selectbox(
                "Caption Style:",
                list(styles.keys()),
                index=list(styles.keys()).index(st.session_state.autocaptions.get("selected_style", "tiktok")),
                format_func=lambda x: x.replace("_", " ").title(),
                key="style_select"
            )
            st.session_state.autocaptions["selected_style"] = selected_style
            
            # Get available transcription engines
            engines = get_available_transcription_engines()
            engine_names = {
                "auto": "Auto-detect",
                "whisper": "OpenAI Whisper",
                "faster_whisper": "Faster Whisper (tiny model available)",
                "vosk": "Vosk (Offline)"
            }
            
            # Engine selection dropdown
            engine = st.selectbox(
                "Transcription Engine:",
                engines,
                index=engines.index(st.session_state.autocaptions.get("engine", "auto")),
                format_func=lambda x: engine_names.get(x, x),
                help="Choose which transcription engine to use. 'Auto' will pick the best available.",
                key="engine_select"
            )
            st.session_state.autocaptions["engine"] = engine
            
            # Model size selection (only relevant for Whisper)
            model_size_disabled = engine == "vosk"
            model_sizes = ["tiny", "base", "small", "medium", "large"]
            if engine == "faster_whisper":
                # Ensure tiny model is first in the list
                model_sizes = model_sizes
                model_size_help = "The tiny model is much faster and uses less memory. Larger models are more accurate but require more processing time."
            else:
                model_size_help = "Larger models are more accurate but require more processing time and resources. Used with Whisper and Faster-Whisper."
                
            model_size = st.selectbox(
                "Transcription Model Size:",
                model_sizes,
                index=model_sizes.index(
                    st.session_state.autocaptions.get("model_size", "base")
                ),
                help=model_size_help,
                key="model_select",
                disabled=model_size_disabled
            )
            if model_size_disabled:
                st.info("Model size selection is only applicable when using Whisper or Faster-Whisper.")
            
            st.session_state.autocaptions["model_size"] = model_size
            
            # Engine-specific notes
            if engine == "faster_whisper":
                st.info("Faster-Whisper supports the tiny model which is much quicker but may be less accurate than larger models.")
            elif engine == "whisper":
                st.info("OpenAI Whisper provides high accuracy but may be slower than Faster-Whisper, especially with larger models.")
            
            # Typography effects selection
            st.markdown("### Typography Effects")
            st.write("Select typography effects to apply to captions:")
            
            # Get current effects or initialize with defaults
            if "typography_effects" not in st.session_state.autocaptions:
                st.session_state.autocaptions["typography_effects"] = []
            
            # Create checkboxes for each effect
            effect_checkboxes = {}
            for effect_name, effect_data in typography_effects.items():
                effect_checkboxes[effect_name] = st.checkbox(
                    f"{effect_name.replace('_', ' ').title()}: {effect_data.get('description', '')}",
                    value=effect_name in st.session_state.autocaptions.get("typography_effects", []),
                    key=f"effect_{effect_name}"
                )
            
            # Update session state with selected effects
            st.session_state.autocaptions["typography_effects"] = [
                effect for effect, selected in effect_checkboxes.items() if selected
            ]
        
        with col2:
            # Display style preview and details
            st.markdown(f"### {selected_style.replace('_', ' ').title()} Style")
            
            # Display style details
            style_details = styles[selected_style]
            st.markdown("**Style Properties:**")
            details_md = f"""
            - **Text Color:** RGB{style_details['text_color']}
            - **Background:** {"None" if not style_details['highlight_color'] else f"RGB{style_details['highlight_color'][:3]} (Alpha: {style_details['highlight_color'][3]})" if len(style_details['highlight_color']) > 3 else f"RGB{style_details['highlight_color']}"}
            - **Position:** {style_details['position'].title()}
            - **Animated:** {"Yes" if style_details['animate'] else "No"}
            - **Word-by-word:** {"Yes" if style_details['word_by_word'] else "No"}
            - **Text Shadow:** {"Yes" if style_details['shadow'] else "No"}
            - **Font Size:** {style_details['font_size']}
            """
            st.markdown(details_md)
            
            # Render sample text visualization
            st.markdown("**Sample Preview:**")
            sample_color = f"rgb{style_details['text_color']}"
            bg_color = "transparent" if not style_details['highlight_color'] else f"rgba{style_details['highlight_color']}"
            text_shadow = "1px 1px 2px #000" if style_details['shadow'] else "none"
            padding = f"{style_details['highlight_padding']}px"
            
            # HTML/CSS for preview
            st.markdown(f"""
            <div style="
                display: flex;
                justify-content: center;
                align-items: center;
                width: 100%;
                height: 100px;
                background-color: #000;
                margin-top: 10px;
                padding: 10px;
                border-radius: 5px;
            ">
                <div style="
                    color: {sample_color};
                    background-color: {bg_color};
                    padding: {padding};
                    border-radius: {padding};
                    font-family: Arial, sans-serif;
                    font-size: {style_details['font_size']}px;
                    font-weight: bold;
                    text-shadow: {text_shadow};
                    text-align: center;
                    max-width: 80%;
                ">
                    Sample Caption Text
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        # Display the generate button and progress
        st.markdown("## Step 3: Generate Captioned Video")
        
        # Check dependencies before processing
        dependencies = check_dependencies()
        if not dependencies["all_available"]:
            st.error(f"Missing required dependencies: {', '.join(dependencies['missing'])}")
            
            # Install missing dependencies button
            if st.button("Install Missing Dependencies", key="install_deps"):
                with st.spinner("Installing dependencies..."):
                    try:
                        for package in dependencies["missing"]:
                            if package == "whisper":
                                # Install OpenAI Whisper
                                st.info("Installing OpenAI Whisper (this may take a while)...")
                                os.system(f"{sys.executable} -m pip install openai-whisper")
                            elif package == "moviepy":
                                st.info("Installing MoviePy...")
                                os.system(f"{sys.executable} -m pip install moviepy")
                            elif package == "pillow":
                                st.info("Installing Pillow...")
                                os.system(f"{sys.executable} -m pip install pillow")
                        
                        st.success("Dependencies installed! Please refresh the page.")
                    except Exception as e:
                        st.error(f"Error installing dependencies: {str(e)}")
        else:
            # Process button
            if st.button("Generate Captioned Video", type="primary", key="generate_button"):
                # Set up progress reporting
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(progress, message):
                    # This will be called from the captioning process
                    progress_bar.progress(min(1.0, progress / 100))
                    status_text.text(f"{message} ({int(progress)}%)")
                
                with st.spinner("Processing video..."):
                    try:
                        # Call the captioning function
                        video_path = st.session_state.autocaptions["source_video"]
                        
                        # Validate video path
                        if not video_path:
                            st.error("No video file selected. Please select a video first.")
                            return
                            
                        if not os.path.exists(video_path):
                            st.error(f"The selected video file does not exist: {video_path}")
                            return
                            
                        style_name = st.session_state.autocaptions["selected_style"]
                        model_size = st.session_state.autocaptions["model_size"]
                        engine = st.session_state.autocaptions["engine"]
                        
                        # Get selected typography effects
                        selected_effects = st.session_state.autocaptions.get("typography_effects", [])
                        
                        # Check if we need to customize the style with effects
                        custom_style = None
                        if selected_effects:
                            # Create a custom style based on the selected style but with our effects
                            try:
                                from utils.video.captions import CAPTION_STYLES
                                base_style = CAPTION_STYLES.get(style_name, {}).copy()
                                base_style["typography_effects"] = selected_effects
                                custom_style = base_style
                            except ImportError:
                                st.warning("Could not load base styles, using selected style without custom effects")
                        
                        # Pre-processing progress update
                        update_progress(10, "Preparing for captioning")
                        
                        # Define output path
                        timestamp = int(time.time())
                        try:
                            if "user_project" in st.session_state and "project_dir" in st.session_state.user_project:
                                output_dir = os.path.join(st.session_state.user_project["project_dir"], "output")
                            else:
                                output_dir = "output"
                            
                            # Ensure output directory exists
                            os.makedirs(output_dir, exist_ok=True)
                            
                            # Verify output directory is writable
                            if not os.access(output_dir, os.W_OK):
                                # Fall back to a temporary directory if needed
                                import tempfile
                                output_dir = tempfile.gettempdir()
                                st.warning(f"Output directory not writable. Using temporary directory: {output_dir}")
                                
                            output_path = os.path.join(output_dir, f"captioned_video_{timestamp}.mp4")
                        except Exception as e:
                            st.error(f"Error setting up output directory: {str(e)}")
                            # Fallback to temp directory
                            import tempfile
                            output_dir = tempfile.gettempdir()
                            output_path = os.path.join(output_dir, f"captioned_video_{timestamp}.mp4")
                            st.warning(f"Using temporary directory for output: {output_dir}")
                        
                        # Mid-processing progress update
                        update_progress(15, "Starting transcription")
                        
                        # Add captions to the video
                        result = add_captions_to_video(
                            video_path=video_path,
                            output_path=output_path,
                            style_name=style_name,
                            model_size=model_size,
                            engine=engine,
                            custom_style=custom_style  # Pass the custom style with effects
                        )
                        
                        # Ensure result is a properly formatted dictionary
                        if not isinstance(result, dict):
                            # Handle non-dictionary return values (should not happen after our fix)
                            result = {"status": "error", "message": "Invalid result format from caption function"}
                        elif "status" not in result:
                            # Ensure there's a status key
                            result["status"] = "error"
                            if "message" not in result:
                                result["message"] = "Invalid result format from caption function"
                        
                        # Process result
                        if result["status"] == "success":
                            # Set successful status
                            st.session_state.autocaptions["status"] = "complete"
                            st.session_state.autocaptions["output_path"] = result["output_path"]
                            
                            # Finish progress
                            update_progress(100, "Captioning complete")
                            
                            # Mark this step as complete
                            mark_step_complete("autocaptions")
                            
                            # Success message
                            st.success("Captioning completed successfully!")
                            
                            # Display the captioned video
                            st.markdown("## 🎉 Captioned Video Result")
                            st.video(result["output_path"])
                            
                            # Display download link
                            st.markdown(f"### [Download Captioned Video]({result['output_path']})")
                        else:
                            # Handle error
                            st.session_state.autocaptions["status"] = "error"
                            st.session_state.autocaptions["error"] = result["message"]
                            
                            # Display error message
                            st.error(f"Captioning failed: {result['message']}")
                            
                            # Show traceback in expander if available
                            if "traceback" in result:
                                with st.expander("Error Details"):
                                    st.code(result["traceback"])
                    
                    except Exception as e:
                        # Handle unexpected error
                        st.session_state.autocaptions["status"] = "error"
                        st.session_state.autocaptions["error"] = str(e)
                        
                        st.error(f"Unexpected error during captioning: {str(e)}")
                        with st.expander("Error Details"):
                            st.code(traceback.format_exc())
        
        # Display previous result if available
        if st.session_state.autocaptions["status"] == "complete" and st.session_state.autocaptions["output_path"]:
            output_path = st.session_state.autocaptions["output_path"]
            if os.path.exists(output_path):
                st.markdown("## Previous Captioned Video")
                st.video(output_path)
                st.markdown(f"### [Download Previous Captioned Video]({output_path})")
    
    # Add dependency installation section
    with st.expander("Manage Dependencies"):
        st.markdown("### Required Dependencies")
        st.markdown("""
        The autocaption feature requires the following dependencies:
        - **MoviePy**: For video processing
        - **OpenAI Whisper**: For speech recognition and transcription
        - **Pillow (PIL)**: For image processing
        - **FFmpeg**: For audio/video encoding/decoding
        """)
        
        # Check for dependencies
        dep_status = check_dependencies()
        if dep_status["all_available"]:
            st.success("All required dependencies are installed!")
        else:
            st.warning(f"Missing dependencies: {', '.join(dep_status['missing'])}")
            if st.button("Install Missing Dependencies", key="install_deps_expander"):
                with st.spinner("Installing dependencies..."):
                    try:
                        for package in dep_status["missing"]:
                            if package == "whisper":
                                # Install OpenAI Whisper
                                st.info("Installing OpenAI Whisper (this may take a while)...")
                                os.system(f"{sys.executable} -m pip install openai-whisper")
                            elif package == "moviepy":
                                st.info("Installing MoviePy...")
                                os.system(f"{sys.executable} -m pip install moviepy")
                            elif package == "pillow":
                                st.info("Installing Pillow...")
                                os.system(f"{sys.executable} -m pip install pillow")
                        
                        st.success("Dependencies installed! Please refresh the page.")
                    except Exception as e:
                        st.error(f"Error installing dependencies: {str(e)}")
        
        # Add FFmpeg info
        st.markdown("### FFmpeg Installation")
        st.markdown("""
        FFmpeg is required for audio and video processing. If it's not installed:
        
        - **macOS**: Install with Homebrew: `brew install ffmpeg`
        - **Windows**: Download from [FFmpeg.org](https://ffmpeg.org/download.html) or install with Chocolatey: `choco install ffmpeg`
        - **Linux**: Install with your package manager, e.g., `sudo apt install ffmpeg`
        """)

# Navigation buttons
st.markdown("---")
render_step_navigation(
    current_step=7,
    prev_step_path="pages/6_Video_Assembly.py",
    next_step_path=None
)

# Run the main function
if __name__ == "__main__":
    main() 