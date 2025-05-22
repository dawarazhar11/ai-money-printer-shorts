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

# Add import for default B-roll IDs
from utils.video.broll_defaults import DEFAULT_BROLL_IDS, get_default_broll_id

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
    st.session_state.broll_type = "video"
if "ollama_models" not in st.session_state:
    st.session_state.ollama_models = []
if "generating_prompts" not in st.session_state:
    st.session_state.generating_prompts = False
if "selected_ollama_model" not in st.session_state:
    st.session_state.selected_ollama_model = None

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
        # Print debug information about the model being used
        print(f"Generating prompt using model: {model}")
        
        # Create a thoughtful prompt for the LLM
        video_or_image = "video" if is_video else "image"
        resolution = settings.get("resolution", "1080x1920")  # Default to 9:16 ratio
        
        prompt_instructions = f"""
        Create a detailed, cinematic, and visually rich {video_or_image} generation prompt based on this text: "{segment_text}"
        
        The theme is: {theme}
        Target resolution: {resolution} (9:16 ratio)
        
        Your prompt should:
        1. Create a vivid, detailed scene with a clear subject/focus
        2. Include rich details about:
           - Setting and environment
           - Lighting, mood, and atmosphere
           - Color palette and visual tone
           - Camera angle, framing, and composition
           - Subject positioning and activity
           - Background elements and context
        3. Tell a mini-story within the scene
        4. Avoid generic terms like "4K" or "HD" (resolution is already defined)
        5. Be 2-4 sentences maximum with descriptive, evocative language
        
        Here's an excellent example of the level of detail and storytelling I want:
        "A large orange octopus is seen resting on the bottom of the ocean floor, blending in with the sandy and rocky terrain. Its tentacles are spread out around its body, and its eyes are closed. The octopus is unaware of a king crab that is crawling towards it from behind a rock, its claws raised and ready to attack. The scene is captured from a wide angle, showing the vastness and depth of the ocean. The water is clear and blue, with rays of sunlight filtering through."
        
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
        return f"A detailed {video_or_image} showing {segment_text}, set in a {theme} environment with atmospheric lighting and rich visual elements."
    except Exception as e:
        st.error(f"Error generating prompt: {str(e)}")
        return f"A detailed {video_or_image} showing {segment_text}, set in a {theme} environment with atmospheric lighting and rich visual elements."

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

# Display the B-Roll type selection
broll_type = st.radio(
    "Select B-Roll Type:",
    ["Video", "Image"],
    index=0 if st.session_state.broll_type.lower() == "video" else 1,
    key="broll_type_selector"
)

# Update session state with the selected B-Roll type (store in lowercase)
st.session_state.broll_type = broll_type.lower()

# Show debug info about the selected type
st.info(f"Selected B-Roll type: **{broll_type}** (stored as '{st.session_state.broll_type}')")

# Show default B-roll IDs
with st.expander("Default B-Roll IDs (Use these for quick assembly)", expanded=False):
    st.info("These IDs will be used automatically in the Video Assembly if no other B-roll content is selected.")
    
    for i, broll_id in enumerate(DEFAULT_BROLL_IDS):
        st.code(f"Segment {i}: {broll_id}", language="text")
    
    st.markdown("""
    **Note:** These default IDs are pre-configured to work with the assembly process.
    Changing these requires modifying the code in `utils/video/broll_defaults.py`.
    """)

# AI model selection for prompt generation
st.subheader("Prompt Generation")

# Connect to Ollama API
if "ollama_models" not in st.session_state or not st.session_state.ollama_models:
    with st.spinner("Connecting to Ollama API..."):
        st.session_state.ollama_models = get_ollama_models()

if st.session_state.ollama_models:
    # Store previous selection to compare
    previous_model = st.session_state.get("selected_ollama_model", None)
    
    # Display model selection dropdown
    selected_model = st.selectbox(
        "Select Ollama Model for Prompt Generation",
        options=st.session_state.ollama_models,
        index=st.session_state.ollama_models.index(previous_model) if previous_model in st.session_state.ollama_models else 0,
        help="Choose an AI model to generate your B-Roll prompts",
        key="model_selectbox"
    )
    
    # Store selected model in session state
    st.session_state.selected_ollama_model = selected_model
    
    # Debug info about selected model
    st.info(f"Using model: **{selected_model}**", icon="ℹ️")
    
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
                
                # Get current model from session state
                current_model = st.session_state.selected_ollama_model
                
                for i, segment in enumerate(broll_segments):
                    segment_id = f"segment_{i}"
                    status_text.text(f"Generating prompt for segment {i+1} of {len(broll_segments)}...")
                    
                    # Determine if we should generate video or image prompt based on broll_type
                    is_video = False
                    if st.session_state.broll_type.lower() == "video":
                        is_video = True
                    elif st.session_state.broll_type == "mixed":
                        # Alternate between video and image for mixed type
                        is_video = (i % 2 == 0)
                    
                    # Print debug information about the content type
                    print(f"Generating {i+1}/{len(broll_segments)} as {'video' if is_video else 'image'} (broll_type: {st.session_state.broll_type})")
                    
                    # Generate the prompt using the current model from session state
                    prompt = generate_prompt_with_ollama(
                        current_model, 
                        segment["content"], 
                        st.session_state.script_theme,
                        is_video
                    )
                    
                    # Generate negative prompt using the same model
                    negative_prompt = generate_negative_prompt(current_model, prompt)
                    
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
                    if st.session_state.broll_type == "mixed":
                        is_video = st.checkbox("Generate as video", 
                                             value=prompt_data.get("is_video", False),
                                             key=f"is_video_{segment_id}")
                    else:
                        is_video = True if st.session_state.broll_type.lower() == "video" else False
                
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
                        # Get current model from session state
                        current_model = st.session_state.selected_ollama_model
                        
                        # Show which model is being used
                        st.info(f"Using model: **{current_model}**", icon="ℹ️")
                        
                        new_prompt = generate_prompt_with_ollama(
                            current_model, 
                            segment["content"], 
                            st.session_state.script_theme,
                            is_video
                        )
                        prompt = new_prompt
                        
                        # Generate new negative prompt
                        new_negative = generate_negative_prompt(current_model, new_prompt)
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
        save_broll_prompts(updated_prompts, st.session_state.broll_type)
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
        # More diverse lists of elements to choose from for prompts
        shot_types = [
            "Close-up", "Medium shot", "Wide angle", "Overhead view", "Side profile", 
            "Low angle shot", "POV shot", "Tracking shot", "Dutch angle", "Aerial view"
        ]
        visual_styles = [
            "cinematic", "documentary style", "professional", "elegant", "dramatic", 
            "minimalist", "vibrant", "moody", "stylized", "naturalistic", "painterly"
        ]
        lighting = [
            "soft natural light", "dramatic lighting", "studio lighting", "golden hour", 
            "morning light", "blue hour", "backlit", "silhouette", "dappled light", 
            "harsh midday sun", "warm evening glow", "cool moonlight"
        ]
        environments = [
            "urban setting", "natural landscape", "indoor environment", "studio setting",
            "coastal scene", "forest setting", "mountainous terrain", "desert landscape",
            "underwater scene", "corporate environment", "rustic setting", "futuristic space"
        ]
        color_palettes = [
            "warm earthy tones", "cool blues and greens", "vibrant contrasting colors",
            "monochromatic palette", "pastel colors", "rich saturated colors",
            "muted tones", "high contrast black and white", "complementary colors"
        ]
        storytelling_elements = [
            "moment of tension", "peaceful scene", "action in progress", "emotional moment",
            "before and after", "cause and effect", "unexpected juxtaposition",
            "revealing detail", "symbolic imagery", "character interaction"
        ]
        
        # Generate prompts
        prompts = {}
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for i, segment in enumerate(broll_segments):
            segment_id = f"segment_{i}"
            status_text.text(f"Generating prompt for segment {i+1} of {len(broll_segments)}...")
            
            # Get content and theme
            content = segment["content"]
            theme = st.session_state.script_theme
            
            # Select random elements from each category
            shot = random.choice(shot_types)
            style = random.choice(visual_styles)
            light = random.choice(lighting)
            environment = random.choice(environments)
            colors = random.choice(color_palettes)
            story_element = random.choice(storytelling_elements)
            
            # Determine if we should generate video or image prompt based on broll_type
            is_video = False
            if st.session_state.broll_type.lower() == "video":
                is_video = True
            elif st.session_state.broll_type == "mixed":
                is_video = (i % 2 == 0)
            
            # Print debug information about the content type
            print(f"Offline generator: {i+1}/{len(broll_segments)} as {'video' if is_video else 'image'} (broll_type: {st.session_state.broll_type})")
            
            # Create a cinematic narrative prompt
            if is_video:
                motion_terms = [
                    "slow motion", "timelapse", "panning shot", "moving camera", 
                    "smooth tracking", "dolly zoom", "steady cam", "crane shot",
                    "aerial movement", "gentle motion", "dynamic camera movement"
                ]
                motion = random.choice(motion_terms)
                
                # Build a more detailed narrative prompt
                story_context = f"A {shot.lower()} captures {content}. "
                visual_details = f"The scene features {environment} with {light}, creating a {style} feel with {colors}. "
                narrative_element = f"The {story_element} unfolds as the {motion} reveals important details. "
                
                prompt = story_context + visual_details + narrative_element
            else:
                # Build a more detailed static image prompt
                story_context = f"A {shot.lower()} depicts {content}. "
                visual_details = f"Set in {environment} with {light}, the composition has a {style} quality with {colors}. "
                narrative_element = f"The image captures a {story_element} that tells a story about the theme of {theme}. "
                
                prompt = story_context + visual_details + narrative_element
            
            # Create negative prompt
            negative_prompt = "poor quality, blurry, distorted faces, bad anatomy, ugly, unrealistic, deformed, low resolution, amateur, poorly composed, out of frame, pixelated, watermark, signature, text, low contrast, dull colors, overexposed, underexposed"
            
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
        st.success("Cinematic prompts generated successfully!")
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