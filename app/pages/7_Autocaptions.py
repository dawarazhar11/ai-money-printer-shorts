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
    from components.progress import render_step_header, mark_step_complete
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
            temp_path = os.path.join("output", f"uploaded_{int(time.time())}.mp4")
            os.makedirs(os.path.dirname(temp_path), exist_ok=True)
            
            with open(temp_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.session_state.autocaptions["source_video"] = temp_path
            st.success(f"Video uploaded successfully: {os.path.basename(temp_path)}")
            
            # Display the video
            st.video(temp_path)
    
    # Display the caption style selection
    if st.session_state.autocaptions["source_video"]:
        st.markdown("## Step 2: Choose Caption Style")
        
        # Get available styles
        styles = get_available_caption_styles()
        
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
            
            # Model size selection
            model_size = st.selectbox(
                "Transcription Model Size:",
                ["tiny", "base", "small", "medium", "large"],
                index=["tiny", "base", "small", "medium", "large"].index(
                    st.session_state.autocaptions.get("model_size", "base")
                ),
                help="Larger models are more accurate but require more processing time and resources",
                key="model_select"
            )
            st.session_state.autocaptions["model_size"] = model_size
        
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
                        style_name = st.session_state.autocaptions["selected_style"]
                        model_size = st.session_state.autocaptions["model_size"]
                        
                        # Pre-processing progress update
                        update_progress(10, "Preparing for captioning")
                        
                        # Define output path
                        timestamp = int(time.time())
                        if "user_project" in st.session_state and "project_dir" in st.session_state.user_project:
                            output_dir = os.path.join(st.session_state.user_project["project_dir"], "output")
                        else:
                            output_dir = "output"
                        
                        os.makedirs(output_dir, exist_ok=True)
                        output_path = os.path.join(output_dir, f"captioned_video_{timestamp}.mp4")
                        
                        # Mid-processing progress update
                        update_progress(15, "Starting transcription")
                        
                        # Add captions to the video
                        result = add_captions_to_video(
                            video_path=video_path,
                            output_path=output_path,
                            style_name=style_name,
                            model_size=model_size
                        )
                        
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

# Run the main function
if __name__ == "__main__":
    main() 