import streamlit as st
import os
import sys
import json
import requests
from pathlib import Path
import re
import time
import random

# Add the app directory to Python path for relative imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from components.navigation import render_workflow_navigation, render_step_navigation
from components.progress import render_step_header
from utils.session_state import get_settings, get_project_path, mark_step_complete

# Set page configuration
st.set_page_config(
    page_title="B-Roll Prompt Generation | AI Money Printer",
    page_icon="🔍",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Load custom CSS
def load_css():
    css_file = Path("assets/css/style.css")
    if css_file.exists():
        with open(css_file, "r") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# Apply custom CSS to fix sidebar text color
st.markdown("""
<style>
    /* Target sidebar with higher specificity */
    [data-testid="stSidebar"] {
        background-color: white !important;
    }
    
    /* Ensure all text inside sidebar is black */
    [data-testid="stSidebar"] * {
        color: black !important;
    }
    
    /* Make sidebar buttons light blue */
    [data-testid="stSidebar"] button {
        background-color: #e6f2ff !important; /* Light blue background */
        color: #0066cc !important; /* Darker blue text */
        border-radius: 6px !important;
    }
    
    /* Hover effect for sidebar buttons */
    [data-testid="stSidebar"] button:hover {
        background-color: #cce6ff !important; /* Slightly darker blue on hover */
    }
    
    /* Target specific sidebar elements with higher specificity */
    .st-emotion-cache-16txtl3, 
    .st-emotion-cache-16idsys, 
    .st-emotion-cache-7ym5gk,
    [data-testid="stSidebar"] a,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] span {
        color: black !important;
    }
    
    /* Target sidebar navigation specifically */
    section[data-testid="stSidebar"] > div > div > div > div > div > ul,
    section[data-testid="stSidebar"] > div > div > div > div > div > ul * {
        color: black !important;
    }
    
    /* Ensure sidebar background stays white even after loading */
    section[data-testid="stSidebar"] > div {
        background-color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# Render navigation sidebar
render_workflow_navigation()

# Load settings
settings = get_settings()
project_path = get_project_path()

# Constants
OLLAMA_API_URL = "http://100.115.243.42:11434/api"
COMFYUI_IMAGE_API_URL = "http://100.115.243.42:8000"
COMFYUI_VIDEO_API_URL = "http://100.86.185.76:8000"
JSON_TEMPLATES = {
    "image": "image_homepc.json",
    "video": "wan.json"
}

# Initialize session state variables
if "segments" not in st.session_state:
    st.session_state.segments = []
if "script_theme" not in st.session_state:
    st.session_state.script_theme = ""
if "broll_prompts" not in st.session_state:
    st.session_state.broll_prompts = {}
if "broll_type" not in st.session_state:
    st.session_state.broll_type = "mixed"
if "ollama_models" not in st.session_state:
    st.session_state.ollama_models = []
if "generating_prompts" not in st.session_state:
    st.session_state.generating_prompts = False

# Function to get available Ollama models
def get_ollama_models():
    try:
        response = requests.get(f"{OLLAMA_API_URL}/tags", timeout=5)
        if response.status_code == 200:
            models = [model['name'] for model in response.json().get('models', [])]
            return models
        return []
    except Exception as e:
        st.sidebar.error(f"Error connecting to Ollama API: {str(e)}")
        return []

# Function to load saved script and segments
def load_script_data():
    script_file = project_path / "script.json"
    if script_file.exists():
        with open(script_file, "r") as f:
            data = json.load(f)
            st.session_state.segments = data.get("segments", [])
            st.session_state.script_theme = data.get("theme", "")
            return True
    return False

# Function to load saved B-Roll prompts
def load_broll_prompts():
    prompts_file = project_path / "broll_prompts.json"
    if prompts_file.exists():
        with open(prompts_file, "r") as f:
            st.session_state.broll_prompts = json.load(f)
            if "broll_type" in st.session_state.broll_prompts:
                st.session_state.broll_type = st.session_state.broll_prompts["broll_type"]
            return True
    return False

# Function to save B-Roll prompts
def save_broll_prompts(prompts, broll_type):
    prompts_file = project_path / "broll_prompts.json"
    data = {
        "prompts": prompts,
        "broll_type": broll_type
    }
    with open(prompts_file, "w") as f:
        json.dump(data, f, indent=4)
    st.session_state.broll_prompts = data
    return True

# Function to generate prompt with Ollama - with improved error handling
def generate_prompt_with_ollama(model, segment_text, theme, is_video=False):
    try:
        # Create a thoughtful prompt for the LLM
        video_or_image = "video" if is_video else "image"
        resolution = settings.get("resolution", "1080x1920")  # Default to 9:16 ratio
        
        prompt_instructions = f"""
        Create a detailed, high-quality {video_or_image} generation prompt based on this text: "{segment_text}"
        
        The theme is: {theme}
        Target resolution: {resolution} (9:16 ratio)
        
        Your prompt should:
        1. Be visually descriptive and detailed (lighting, color, mood, composition, style)
        2. Follow professional prompt engineering best practices
        3. Be optimized for {video_or_image} generation with {'Wan' if is_video else 'ComfyUI'}
        4. Be 1-3 sentences maximum, using commas to separate concepts
        5. NOT include negative prompts - I'll generate those separately
        
        Return ONLY the prompt text, nothing else. No explanations, no "Prompt:" prefix, just the prompt itself.
        """
        
        # Increase timeout and add retry logic
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                # Increase timeout to 60 seconds
                response = requests.post(
                    f"{OLLAMA_API_URL}/generate",
                    json={
                        "model": model,
                        "prompt": prompt_instructions,
                        "stream": False
                    },
                    timeout=60
                )
                
                if response.status_code == 200:
                    generated_prompt = response.json().get('response', '').strip()
                    return generated_prompt
                else:
                    st.warning(f"Error from Ollama API: {response.status_code} - {response.text}")
                    current_retry += 1
                    time.sleep(1)  # Wait before retrying
            except requests.exceptions.Timeout:
                current_retry += 1
                st.warning(f"Timeout connecting to Ollama API (attempt {current_retry}/{max_retries})")
                time.sleep(2)  # Wait longer before retrying
            except Exception as e:
                current_retry += 1
                st.warning(f"Error connecting to Ollama API: {str(e)}")
                time.sleep(1)  # Wait before retrying
                
        # If we've exhausted retries, return a fallback prompt
        return f"A {video_or_image} about {theme} featuring {segment_text}"
    except Exception as e:
        st.error(f"Error generating prompt: {str(e)}")
        return f"A {video_or_image} about {theme} featuring {segment_text}"

# Function to generate negative prompts automatically - with improved error handling
def generate_negative_prompt(model, prompt):
    try:
        # Default negative prompt to use if API call fails
        default_negative = "poor quality, blurry, distorted faces, bad anatomy, ugly, unrealistic, deformed, low resolution, amateur, poorly composed, out of frame, pixelated, watermark, signature, text"
        
        negative_instructions = f"""
        Based on this prompt: "{prompt}"
        
        Generate a negative prompt for image/video generation that will help avoid common issues.
        Include terms to avoid: poor quality, blurry, distorted faces, bad anatomy, ugly, unrealistic, 
        deformed, low resolution, amateur, poorly composed, and any other elements that would lower quality.
        
        Return ONLY the negative prompt text - no explanations or additional context.
        """
        
        # Increase timeout and add retry logic
        max_retries = 2  # Fewer retries for negative prompt since we have a good default
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                # Increase timeout to 45 seconds
                response = requests.post(
                    f"{OLLAMA_API_URL}/generate",
                    json={
                        "model": model,
                        "prompt": negative_instructions,
                        "stream": False
                    },
                    timeout=45
                )
                
                if response.status_code == 200:
                    negative_prompt = response.json().get('response', '').strip()
                    return negative_prompt
                else:
                    current_retry += 1
                    time.sleep(1)  # Wait before retrying
            except Exception as e:
                current_retry += 1
                time.sleep(1)  # Wait before retrying
                
        # If we've exhausted retries, return the default negative prompt
        return default_negative
    except Exception as e:
        # Return a default negative prompt if there's an exception
        return default_negative

# Page header
render_step_header(4, "B-Roll Prompt Generation", 8)
st.title("🔍 B-Roll Prompt Generation")
st.markdown("""
Generate optimized prompts for your B-Roll segments that will be used to create visuals with Wan and ComfyUI.
These prompts will be tailored to match your script segments and overall theme.
""")

# Load script data
has_script = load_script_data()
if not has_script:
    st.error("No script found. Please complete the Script Segmentation step first.")
    st.stop()

# Load saved prompts if they exist
has_prompts = load_broll_prompts()

# Get B-Roll segments
broll_segments = [segment for segment in st.session_state.segments if segment["type"] == "B-Roll"]
if not broll_segments:
    st.warning("No B-Roll segments found in your script. Please go back and add B-Roll segments.")
    
# Display script theme
st.subheader("Script Theme")
st.info(f"Current theme: **{st.session_state.script_theme}**")

# B-Roll type selection
st.subheader("B-Roll Type")
broll_type = st.radio(
    "Select B-Roll content type",
    options=["videos", "images", "mixed"],
    index=["videos", "images", "mixed"].index(st.session_state.broll_type),
    help="Choose what type of B-Roll content you want to generate"
)
st.session_state.broll_type = broll_type

# AI model selection for prompt generation
st.subheader("Prompt Generation")

# Connect to Ollama API
if "ollama_models" not in st.session_state or not st.session_state.ollama_models:
    with st.spinner("Connecting to Ollama API..."):
        st.session_state.ollama_models = get_ollama_models()

if st.session_state.ollama_models:
    selected_model = st.selectbox(
        "Select Ollama Model for Prompt Generation",
        options=st.session_state.ollama_models,
        index=0 if st.session_state.ollama_models else None,
        help="Choose an AI model to generate your B-Roll prompts"
    )
    
    # Generate all prompts button
    generate_col1, generate_col2 = st.columns([2, 1])
    with generate_col1:
        st.markdown("Generate prompts for all B-Roll segments")
    with generate_col2:
        if st.button("🤖 Generate All Prompts", use_container_width=True):
            if broll_segments:
                st.session_state.generating_prompts = True
                prompts = {}
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, segment in enumerate(broll_segments):
                    segment_id = f"segment_{i}"
                    status_text.text(f"Generating prompt for segment {i+1} of {len(broll_segments)}...")
                    
                    # Determine if we should generate video or image prompt based on broll_type
                    is_video = False
                    if broll_type == "videos":
                        is_video = True
                    elif broll_type == "mixed":
                        # Alternate between video and image for mixed type
                        is_video = (i % 2 == 0)
                    
                    # Generate the prompt
                    prompt = generate_prompt_with_ollama(
                        selected_model, 
                        segment["content"], 
                        st.session_state.script_theme,
                        is_video
                    )
                    
                    # Generate negative prompt
                    negative_prompt = generate_negative_prompt(selected_model, prompt)
                    
                    # Store both prompts
                    prompts[segment_id] = {
                        "prompt": prompt,
                        "negative_prompt": negative_prompt,
                        "is_video": is_video,
                        "segment_text": segment["content"]
                    }
                    
                    # Update progress
                    progress_bar.progress((i + 1) / len(broll_segments))
                
                status_text.empty()
                
                # Save prompts to session state and file
                save_broll_prompts(prompts, broll_type)
                st.session_state.generating_prompts = False
                st.success("All prompts generated successfully!")
                st.rerun()
            else:
                st.warning("No B-Roll segments to generate prompts for.")
else:
    st.warning(f"Could not connect to Ollama API at {OLLAMA_API_URL}. Please check the connection and refresh.")
    if st.button("Refresh Ollama Connection"):
        st.session_state.ollama_models = get_ollama_models()
        st.rerun()

# Display and edit B-Roll prompts
if "prompts" in st.session_state.broll_prompts and st.session_state.broll_prompts["prompts"]:
    st.subheader("Review and Edit B-Roll Prompts")
    
    prompts = st.session_state.broll_prompts["prompts"]
    updated_prompts = {}
    
    for i, segment in enumerate(broll_segments):
        segment_id = f"segment_{i}"
        
        if segment_id in prompts:
            prompt_data = prompts[segment_id]
            
            with st.expander(f"B-Roll Segment {i+1}", expanded=True):
                st.markdown(f"**Segment Text:** {segment['content']}")
                
                # Display content type
                content_type = "Video" if prompt_data.get("is_video", False) else "Image"
                content_col1, content_col2 = st.columns([3, 1])
                with content_col1:
                    st.markdown(f"**Content Type:** {content_type}")
                with content_col2:
                    if broll_type == "mixed":
                        is_video = st.checkbox("Generate as video", 
                                             value=prompt_data.get("is_video", False),
                                             key=f"is_video_{segment_id}")
                    else:
                        is_video = True if broll_type == "videos" else False
                
                # Prompt text area
                prompt = st.text_area(
                    "Prompt",
                    value=prompt_data.get("prompt", ""),
                    height=100,
                    key=f"prompt_{segment_id}"
                )
                
                # Negative prompt text area
                negative_prompt = st.text_area(
                    "Negative Prompt",
                    value=prompt_data.get("negative_prompt", ""),
                    height=100,
                    key=f"negative_{segment_id}"
                )
                
                # Regenerate single prompt button
                if st.button("🔄 Regenerate Prompt", key=f"regen_{segment_id}"):
                    with st.spinner("Regenerating prompt..."):
                        new_prompt = generate_prompt_with_ollama(
                            selected_model, 
                            segment["content"], 
                            st.session_state.script_theme,
                            is_video
                        )
                        prompt = new_prompt
                        
                        # Generate new negative prompt
                        new_negative = generate_negative_prompt(selected_model, new_prompt)
                        negative_prompt = new_negative
                
                # Store updated prompt data
                updated_prompts[segment_id] = {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "is_video": is_video,
                    "segment_text": segment["content"]
                }
        else:
            st.warning(f"No prompt found for segment {i+1}. Please generate prompts for all segments.")
    
    # Save updated prompts
    if st.button("Save All Prompts", type="primary"):
        save_broll_prompts(updated_prompts, broll_type)
        mark_step_complete("step_4")
        st.success("B-Roll prompts saved successfully!")

    # Display JSON config information
    st.subheader("Integration Information")
    st.markdown("""
    ### ComfyUI Configuration
    - For image generation: 100.115.243.42:8188 using image_homepc.json
    - For video generation: 100.86.185.76:8188 using wan.json
    
    The generated prompts are optimized for these endpoints.
    """)
else:
    if has_prompts:
        st.info("Previous prompts were found but require regeneration. Please click 'Generate All Prompts' above.")
    else:
        st.info("No prompts generated yet. Click 'Generate All Prompts' to create optimized prompts for your B-Roll segments.")

# Add a fallback manual generation option
st.markdown("---")
st.subheader("🔧 Manual Prompt Generation")
st.markdown("""
If you're having trouble with the Ollama API or want to quickly generate basic prompts, you can use this simple generator.
This doesn't require Ollama and works offline.
""")

if st.button("Generate Simple Prompts Offline", use_container_width=True):
    if broll_segments:
        # Lists of elements to choose from for prompts
        shot_types = ["Close-up", "Medium shot", "Wide angle", "Overhead view", "Side profile", "Tracking shot", "POV shot"]
        visual_styles = ["cinematic", "documentary style", "professional", "elegant", "dramatic", "minimalist", "vibrant"]
        lighting = ["soft natural light", "dramatic lighting", "studio lighting", "golden hour", "morning light", "blue hour"]
        
        # Generate prompts
        prompts = {}
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, segment in enumerate(broll_segments):
            segment_id = f"segment_{i}"
            status_text.text(f"Generating prompt for segment {i+1} of {len(broll_segments)}...")
            
            # Extract keywords from content
            content = segment["content"].lower()
            keywords = [word for word in content.split() if len(word) > 3 and word not in {"with", "that", "this", "from", "there", "their", "they", "have", "about"}]
            
            # Select random elements
            shot = random.choice(shot_types)
            style = random.choice(visual_styles)
            light = random.choice(lighting)
            
            # Determine if we should generate video or image prompt based on broll_type
            is_video = False
            if broll_type == "videos":
                is_video = True
            elif broll_type == "mixed":
                is_video = (i % 2 == 0)
            
            # Create a basic prompt
            if is_video:
                motion_terms = ["slow motion", "timelapse", "panning shot", "moving camera", "smooth tracking"]
                motion = random.choice(motion_terms)
                prompt = f"{shot} of {content}. {style}, {light}, {motion}. Professional videography, high-quality footage."
            else:
                prompt = f"{shot} of {content}. {style}, {light}. Professional photography, high-quality image."
            
            # Create negative prompt
            negative_prompt = "poor quality, blurry, distorted, ugly, unrealistic, deformed, low resolution, amateur, poorly composed, out of frame, pixelated, watermark, signature, text"
            
            # Store both prompts
            prompts[segment_id] = {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "is_video": is_video,
                "segment_text": segment["content"]
            }
            
            # Update progress
            progress_bar.progress((i + 1) / len(broll_segments))
        
        status_text.empty()
        
        # Save prompts to session state and file
        save_broll_prompts(prompts, broll_type)
        st.success("Simple prompts generated successfully!")
        st.rerun()
    else:
        st.warning("No B-Roll segments to generate prompts for.")

# Navigation buttons
st.markdown("---")
render_step_navigation(
    current_step=4,
    prev_step_path="pages/3_Script_Segmentation.py",
    next_step_path="pages/5_Content_Production.py"
) 