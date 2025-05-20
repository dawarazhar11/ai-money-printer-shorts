import streamlit as st
import os
import sys
import json
import requests
from pathlib import Path
import re
import time

# Add the app directory to Python path for relative imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from components.navigation import render_workflow_navigation, render_step_navigation
from components.progress import render_step_header
from utils.session_state import get_settings, get_project_path, mark_step_complete

# Set page configuration
st.set_page_config(
    page_title="Script Segmentation | AI Money Printer",
    page_icon="✂️",
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

# Render navigation sidebar
render_workflow_navigation()

# Load settings
settings = get_settings()
project_path = get_project_path()

# Initialize session state variables
if "script" not in st.session_state:
    st.session_state.script = ""
if "segments" not in st.session_state:
    st.session_state.segments = []
if "auto_segmented" not in st.session_state:
    st.session_state.auto_segmented = False
if "script_theme" not in st.session_state:
    st.session_state.script_theme = ""
if "generating_script" not in st.session_state:
    st.session_state.generating_script = False
if "ollama_models" not in st.session_state:
    st.session_state.ollama_models = []

# Constants
OLLAMA_API_URL = "http://100.115.243.42:11434/api"

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

# Function to generate script with Ollama
def generate_script_with_ollama(model, theme, video_duration):
    try:
        # Calculate appropriate word count based on video duration
        # Assuming average speaking rate of 150 words per minute
        words_per_second = 2.5  # 150 words per minute / 60 seconds
        target_word_count = int(video_duration * words_per_second)
        
        prompt = f"""Create a short-form video script about '{theme}' for a {video_duration} second video. 
        The script should be approximately {target_word_count} words, which fits into a {video_duration}-second video.
        The script should include an engaging introduction, a few key points, and a strong conclusion.
        Make the script conversational, engaging, and suitable for a talking head video with B-roll footage.
        DO NOT include any instructions, notes or headers - ONLY output the actual script.
        """
        
        response = requests.post(
            f"{OLLAMA_API_URL}/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get('response', '')
        else:
            return f"Error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Error generating script: {str(e)}"

# Function to load saved themes
def load_saved_themes():
    """Load previously used themes"""
    themes_file = Path("config/user_data/themes.json")
    if themes_file.exists():
        with open(themes_file, "r") as f:
            return json.load(f)
    return []

# Function to save a new theme
def save_theme(theme):
    """Save a new theme to the themes list"""
    if not theme or theme.strip() == "":
        return
    
    themes = load_saved_themes()
    if theme not in themes:
        themes.append(theme)
        
        # Create config directory if it doesn't exist
        config_dir = Path("config/user_data")
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Save themes to JSON file
        with open(config_dir / "themes.json", "w") as f:
            json.dump(themes, f, indent=4)

# Function to load saved script if exists
def load_saved_script():
    script_file = project_path / "script.json"
    if script_file.exists():
        with open(script_file, "r") as f:
            data = json.load(f)
            st.session_state.script = data.get("full_script", "")
            st.session_state.segments = data.get("segments", [])
            st.session_state.script_theme = data.get("theme", "")
            return True
    return False

# Function to save script and segments
def save_script_segments(script, segments, theme):
    script_file = project_path / "script.json"
    data = {
        "full_script": script,
        "segments": segments,
        "theme": theme
    }
    with open(script_file, "w") as f:
        json.dump(data, f, indent=4)
    
    # Save theme to themes list
    save_theme(theme)
    
    return True

# Function to generate B-Roll visual description with Ollama
def generate_broll_description(model, preceding_content, following_content, theme):
    try:
        # Create a thoughtful prompt for the LLM
        prompt_instructions = f"""
        Create a detailed visual description for B-Roll footage based on this context:
        
        Theme of the video: {theme}
        
        Preceding script segment: "{preceding_content}"
        
        Following script segment (if available): "{following_content}"
        
        Your task is to describe a visual scene that would complement this part of the script.
        
        Your description should:
        1. Be specific about what is shown visually (subject, action, setting)
        2. Include camera angles or shot types (close-up, aerial view, etc.)
        3. Mention visual style, mood, and atmosphere
        4. Be relevant to the theme and content of the surrounding script
        5. Be 1-3 sentences maximum, focusing on key visual elements
        
        Do NOT include any explanations or notes - ONLY output the visual description itself.
        """
        
        # Add retry logic with better error handling
        max_retries = 3
        current_retry = 0
        
        while current_retry < max_retries:
            try:
                # Call Ollama API with increased timeout (120 seconds)
                st.info(f"Connecting to Ollama API (attempt {current_retry+1}/{max_retries})...")
                response = requests.post(
                    f"{OLLAMA_API_URL}/generate",
                    json={
                        "model": model,
                        "prompt": prompt_instructions,
                        "stream": False
                    },
                    timeout=120  # Increased timeout to 2 minutes
                )
                
                if response.status_code == 200:
                    generated_description = response.json().get('response', '').strip()
                    if generated_description:
                        st.success("Successfully generated description with Ollama")
                        return generated_description
                    else:
                        st.warning("Ollama returned an empty response, retrying...")
                        current_retry += 1
                        time.sleep(2)
                else:
                    st.warning(f"Ollama API returned status code {response.status_code}, retrying...")
                    current_retry += 1
                    time.sleep(2)
            except requests.exceptions.Timeout:
                st.warning(f"Timeout connecting to Ollama API (attempt {current_retry+1}/{max_retries})")
                current_retry += 1
                time.sleep(3)  # Wait longer before retrying
            except requests.exceptions.ConnectionError:
                st.warning(f"Connection error to Ollama API (attempt {current_retry+1}/{max_retries})")
                current_retry += 1
                time.sleep(3)
            except Exception as e:
                st.warning(f"Error connecting to Ollama API: {str(e)}")
                current_retry += 1
                time.sleep(2)
        
        # If all retries fail, generate a more sophisticated fallback based on context
        st.warning("Could not connect to Ollama. Using fallback description generator.")
        
        # Extract key words from surrounding content and theme
        all_content = f"{theme} {preceding_content} {following_content}"
        words = re.findall(r'\b\w+\b', all_content.lower())
        
        # Count most common words (excluding common stop words)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were'}
        word_counts = {}
        for word in words:
            if word not in stop_words and len(word) > 3:
                word_counts[word] = word_counts.get(word, 0) + 1
        
        # Get top 3 words
        top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        top_words = [word for word, count in top_words]
        
        # Generate fallback description based on theme and key words
        camera_angles = ["Close-up", "Medium shot", "Wide angle", "Overhead view", "Side profile"]
        settings = ["indoor setting", "outdoor location", "natural environment", "urban landscape", "studio setting"]
        moods = ["vibrant", "serene", "dramatic", "peaceful", "energetic", "professional"]
        
        # Use random elements but in a coherent way
        import random
        camera = random.choice(camera_angles)
        setting = random.choice(settings)
        mood = random.choice(moods)
        
        # Build fallback description
        if top_words:
            keywords_str = ", ".join(top_words)
            fallback = f"{camera} of {keywords_str} in a {mood} {setting}. Visual represents key elements related to {theme}."
        else:
            fallback = f"{camera} shot depicting elements related to {theme} in a {mood} {setting}."
        
        return fallback
        
    except Exception as e:
        st.error(f"Error in generate_broll_description: {str(e)}")
        return f"Visual scene related to {theme} with relevant imagery."

# Function for local B-Roll description generation without Ollama
def generate_local_description(preceding_content, following_content, theme):
    # Extract key words from surrounding content and theme
    all_content = f"{theme} {preceding_content} {following_content}"
    words = re.findall(r'\b\w+\b', all_content.lower())
    
    # Count most common words (excluding common stop words)
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'is', 'are', 'was', 'were'}
    word_counts = {}
    for word in words:
        if word not in stop_words and len(word) > 3:
            word_counts[word] = word_counts.get(word, 0) + 1
    
    # Get top 3 words
    top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]
    top_words = [word for word, count in top_words]
    
    # Generate description based on theme and key words
    import random
    
    # Lists of visual elements to choose from
    camera_angles = ["Close-up", "Medium shot", "Wide angle", "Overhead view", "Side profile", "Tracking shot"]
    settings = ["indoor setting", "outdoor location", "natural environment", "urban landscape", "studio setting", "professional workspace"]
    moods = ["vibrant", "serene", "dramatic", "peaceful", "energetic", "professional", "atmospheric", "intimate"]
    actions = ["moving", "working", "flowing", "transforming", "interacting", "showcasing"]
    subjects = ["person", "object", "hands", "scene", "landscape", "product"]
    styles = ["cinematic", "documentary", "stylized", "realistic", "artistic", "clean"]
    
    # Use random elements but in a coherent way
    camera = random.choice(camera_angles)
    setting = random.choice(settings)
    mood = random.choice(moods)
    action = random.choice(actions)
    subject = random.choice(subjects)
    style = random.choice(styles)
    
    # Build description
    if top_words:
        keywords_str = ", ".join(top_words)
        description = f"{camera} of {keywords_str} in a {mood} {setting}. {style.capitalize()} {subject} {action} with {mood} lighting."
    else:
        description = f"{camera} shot in a {mood} {setting} related to {theme}. {style.capitalize()} visuals with {mood} atmosphere."
    
    return description

# Page header
render_step_header(3, "Script Segmentation", 8)
st.title("✂️ Script Segmentation")

# Add a notice about B-Roll changes
st.warning("""
**Important Update:** B-Roll segments now represent visual descriptions only, not spoken content. 
The entire script is contained in A-Roll segments, while B-Roll segments describe the visuals that will appear.
""")

st.markdown("""
Break down your script into alternating A-Roll and B-Roll segments. 
- **A-Roll**: Your on-camera talking segments. These contain the words you'll actually speak.
- **B-Roll**: Complementary visuals only. These are NOT spoken - they're visual descriptions for what will be shown while A-Roll audio plays.

For B-Roll segments, describe the visuals you want to see on screen (e.g., "slow-motion footage of coffee brewing", "aerial view of city at sunset"). These descriptions will be used to generate detailed prompts in the next step.

The script will follow a sequential pattern with A-Roll and B-Roll segments alternating.
The first and last segments will always be A-Roll.
""")

# Check if script was previously saved
has_saved_script = load_saved_script()

# Load saved themes
saved_themes = load_saved_themes()

# Script theme input
st.subheader("Script Theme/Topic")
col1, col2 = st.columns([2, 1])

with col1:
    script_theme = st.text_input(
        "Enter the main theme/topic of your script",
        value=st.session_state.script_theme,
        help="This theme will be used as a seed for generating B-Roll prompts"
    )
    
with col2:
    if saved_themes:
        st.markdown("**Select Previous Theme:**")
        for theme in saved_themes:
            if st.button(theme, key=f"theme_{theme}"):
                script_theme = theme
                st.session_state.script_theme = theme

# AI Script Generation
st.subheader("AI Script Generation")
st.markdown("Let AI generate a script based on your theme and video duration")

# AI model selection
if "ollama_models" not in st.session_state or not st.session_state.ollama_models:
    with st.spinner("Connecting to Ollama API..."):
        st.session_state.ollama_models = get_ollama_models()

col1, col2 = st.columns([2, 1])

# If we have models, show dropdown and generate button
if st.session_state.ollama_models:
    with col1:
        selected_model = st.selectbox(
            "Select AI Model",
            options=st.session_state.ollama_models,
            index=0 if st.session_state.ollama_models else None,
            help="Choose an AI model to generate your script"
        )
    
    with col2:
        if st.button("🤖 Generate Script", use_container_width=True, disabled=not script_theme):
            if not script_theme:
                st.warning("Please enter a theme first")
            else:
                st.session_state.generating_script = True
                with st.spinner(f"Generating script about '{script_theme}'..."):
                    generated_script = generate_script_with_ollama(
                        selected_model, 
                        script_theme, 
                        settings["video_duration"]
                    )
                    st.session_state.script = generated_script
                    script_text = generated_script  # Update the variable for later use
                    st.session_state.generating_script = False
                    st.success("Script generated! Review and edit below if needed.")
else:
    st.warning(f"Could not connect to Ollama API at {OLLAMA_API_URL}. Please check the connection and refresh.")
    if st.button("Refresh Ollama Connection"):
        st.session_state.ollama_models = get_ollama_models()
        st.experimental_rerun()

# Script input section
st.subheader("Enter Your Script")
script_text = st.text_area(
    "Paste or edit your script below",
    value=st.session_state.script,
    height=200,
    help="Enter the complete script for your video",
    placeholder="Enter your complete script here. It will be segmented into A-Roll and B-Roll sections."
)

# Auto-segmentation section
st.subheader("Script Segmentation")
st.markdown("""
Click the button below to automatically segment your script. This will:
1. Divide your script into the appropriate number of A-Roll segments
2. Place placeholder text in B-Roll segments for visual descriptions
3. Ensure all the spoken content is preserved in A-Roll segments only
""")

# Add guidance for writing effective B-Roll descriptions
st.info("""
**Tips for B-Roll Visual Descriptions:**

When describing B-Roll visuals, be specific about:
- **Subject**: What/who is in the scene (e.g., person, landscape, object)
- **Action/Movement**: What is happening (e.g., typing, flowing, spinning)
- **Setting/Environment**: Where the scene takes place (e.g., office, forest, studio)
- **Style/Mood**: The visual tone (e.g., cinematic, bright, dramatic)
- **Camera Angle/Shot**: How it's filmed (e.g., close-up, aerial view, tracking shot)

These descriptions will be converted into detailed image/video generation prompts in the next step.
""")

# Add AI model selection for B-Roll descriptions
if st.session_state.ollama_models:
    st.markdown("### AI-Generated B-Roll Descriptions")
    st.markdown("Use AI to automatically generate visual descriptions for all B-Roll segments.")
    
    # Add option to use local generation instead of Ollama
    use_local_generator = st.checkbox("Use simple local generator (faster, no Ollama required)", value=False, 
                                     help="Select this if Ollama is timing out or unavailable")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Only show model selection if not using local generator
        if not use_local_generator:
            selected_model = st.selectbox(
                "Select AI Model for B-Roll Descriptions",
                options=st.session_state.ollama_models,
                index=0 if st.session_state.ollama_models else None,
                help="Choose an AI model to generate B-Roll visual descriptions"
            )
        else:
            st.info("Using local generator - no AI model needed")
            # Create a hidden placeholder for the selected_model variable
            selected_model = None
    
    with col2:
        st.markdown("### ")  # Add some spacing
        generate_all_button = st.button("🤖 Generate All B-Roll Visuals", type="primary", use_container_width=True)
        
        if generate_all_button:
            if not script_theme:
                st.warning("Please enter a script theme first.")
            elif not st.session_state.segments:
                st.warning("Please segment your script first.")
            else:
                # Store original segments
                original_segments = st.session_state.segments.copy()
                updated_segments = []
                
                # Count B-Roll segments for progress reporting
                broll_count = len([s for s in original_segments if s["type"] == "B-Roll"])
                
                # Create a progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                # Track processing stats
                success_count = 0
                fallback_count = 0
                current_segment = 0
                
                with st.spinner("Generating B-Roll visual descriptions..."):
                    # Loop through all segments
                    for i, segment in enumerate(original_segments):
                        if segment["type"] == "B-Roll":
                            current_segment += 1
                            status_text.text(f"Processing B-Roll segment {current_segment} of {broll_count}...")
                            
                            # Get surrounding A-Roll content for context
                            preceding_content = ""
                            following_content = ""
                            
                            if i > 0 and i-1 < len(original_segments):
                                preceding_content = original_segments[i-1].get("content", "")
                            
                            if i+1 < len(original_segments):
                                following_content = original_segments[i+1].get("content", "")
                            
                            try:
                                # Generate description
                                if use_local_generator:
                                    generated_description = generate_local_description(
                                        preceding_content,
                                        following_content,
                                        script_theme
                                    )
                                else:
                                    generated_description = generate_broll_description(
                                        selected_model,
                                        preceding_content,
                                        following_content,
                                        script_theme
                                    )
                                
                                # Check if we got a real description or a fallback
                                if "fallback" in locals() and generated_description == fallback:
                                    fallback_count += 1
                                else:
                                    success_count += 1
                                
                                # Update segment content
                                updated_segments.append({
                                    "type": segment["type"],
                                    "content": generated_description
                                })
                            except Exception as e:
                                st.error(f"Error processing segment {current_segment}: {str(e)}")
                                # Keep original content to avoid data loss
                                updated_segments.append(segment)
                                fallback_count += 1
                            
                            # Update progress
                            progress_bar.progress(current_segment / broll_count)
                        else:
                            # Keep A-Roll segments as is
                            updated_segments.append(segment)
                    
                    # Update session state
                    st.session_state.segments = updated_segments
                    
                    # Show completion message with stats
                    if success_count > 0:
                        if fallback_count > 0:
                            st.warning(f"Generated {success_count} descriptions successfully. {fallback_count} segments used fallback descriptions due to API issues.")
                        else:
                            st.success(f"All {success_count} B-Roll visual descriptions generated successfully!")
                    else:
                        st.error("Failed to generate any descriptions with Ollama. All segments used fallback descriptions.")
                    
                    st.experimental_rerun()

# Auto-segment script based on number of B-Roll segments
def auto_segment_script(script_text, num_b_roll_segments):
    if not script_text:
        return []
    
    # Split script into sentences
    sentences = re.split(r'(?<=[.!?])\s+', script_text.strip())
    sentences = [s for s in sentences if s.strip()]
    
    if len(sentences) < 2:
        return [{"type": "A-Roll", "content": script_text}]
    
    # Calculate segments
    # Want to have format: A-B-A-B-A... ending with A
    # Total segments = (num_b_roll_segments * 2) + 1
    total_segments = (num_b_roll_segments * 2) + 1
    
    # Calculate how many sentences per A-Roll segment
    # Note: B-Roll segments don't contain script content
    aroll_segments_count = (total_segments + 1) // 2  # Ceiling division to ensure enough A-Roll segments
    sentences_per_aroll = max(1, len(sentences) // aroll_segments_count)
    
    # Create segments
    segments = []
    sentence_index = 0
    
    for i in range(total_segments):
        if i % 2 == 0:
            # A-Roll segments (0, 2, 4, etc.)
            end_idx = min(sentence_index + sentences_per_aroll, len(sentences))
            segment_content = " ".join(sentences[sentence_index:end_idx]).strip()
            segments.append({"type": "A-Roll", "content": segment_content})
            sentence_index = end_idx
        else:
            # B-Roll segments (1, 3, 5, etc.)
            # Use a helpful placeholder for visual descriptions instead of script content
            broll_placeholder = (
                "Describe the visuals you want to see (not what will be said).\n\n"
                "Examples:\n"
                "- Slow-motion shot of coffee beans falling into a grinder\n"
                "- Aerial view of mountains with morning fog\n"
                "- Person walking through busy market with colorful stalls"
            )
            segments.append({
                "type": "B-Roll", 
                "content": broll_placeholder
            })
    
    return segments

# Add option to auto-generate B-Roll descriptions during segmentation
auto_generate_broll = False
auto_use_local = False
if st.session_state.ollama_models:
    cols = st.columns(2)
    with cols[0]:
        auto_generate_broll = st.checkbox("Auto-generate B-Roll descriptions", value=False)
    if auto_generate_broll:
        with cols[1]:
            auto_use_local = st.checkbox("Use local generator", value=False, 
                                       help="Select if Ollama is timing out")

if st.button("Auto-Segment Script"):
    if script_text:
        st.session_state.segments = auto_segment_script(script_text, settings["broll_segments"])
        st.session_state.script = script_text
        st.session_state.script_theme = script_theme
        st.session_state.auto_segmented = True
        
        # If auto-generate is selected and we have either Ollama models or local generator
        if auto_generate_broll and (st.session_state.ollama_models or auto_use_local) and script_theme:
            segment_message = "Auto-generating B-Roll descriptions"
            if auto_use_local:
                segment_message += " using local generator"
            else:
                segment_message += " using Ollama"
                
            with st.spinner(segment_message):
                # Only get model if not using local generator
                model = st.session_state.ollama_models[0] if not auto_use_local and st.session_state.ollama_models else None
                updated_segments = []
                
                # Add progress indicators
                broll_count = len([s for s in st.session_state.segments if s["type"] == "B-Roll"])
                progress_bar = st.progress(0)
                status_text = st.empty()
                current_segment = 0
                
                # Loop through all segments
                for i, segment in enumerate(st.session_state.segments):
                    if segment["type"] == "B-Roll":
                        current_segment += 1
                        status_text.text(f"Processing B-Roll segment {current_segment} of {broll_count}...")
                        
                        # Get surrounding A-Roll content for context
                        preceding_content = ""
                        following_content = ""
                        
                        if i > 0 and i-1 < len(st.session_state.segments):
                            preceding_content = st.session_state.segments[i-1].get("content", "")
                        
                        if i+1 < len(st.session_state.segments):
                            following_content = st.session_state.segments[i+1].get("content", "")
                        
                        try:
                            # Generate description
                            if auto_use_local:
                                generated_description = generate_local_description(
                                    preceding_content,
                                    following_content,
                                    script_theme
                                )
                            else:
                                generated_description = generate_broll_description(
                                    model,
                                    preceding_content,
                                    following_content,
                                    script_theme
                                )
                            
                            # Update segment content
                            updated_segments.append({
                                "type": segment["type"],
                                "content": generated_description
                            })
                        except Exception as e:
                            st.error(f"Error generating description for segment {current_segment}: {str(e)}")
                            # Keep original content in case of error
                            updated_segments.append(segment)
                        
                        # Update progress
                        progress_bar.progress(current_segment / broll_count)
                    else:
                        # Keep A-Roll segments as is
                        updated_segments.append(segment)
                
                # Update session state
                st.session_state.segments = updated_segments
                st.success(f"Script automatically segmented with {broll_count} B-Roll descriptions")
        else:
            st.success(f"Script automatically segmented into {len(st.session_state.segments)} segments")
    else:
        st.warning("Please enter a script before segmenting")

# Display and edit segments
if st.session_state.segments:
    st.markdown("### Review and Edit Segments")
    st.info("You can adjust the segments below. Make sure the content flows naturally between segments.")
    
    updated_segments = []
    
    for i, segment in enumerate(st.session_state.segments):
        with st.expander(f"{segment['type']} - Segment {i+1}", expanded=True):
            segment_type = st.selectbox(
                "Segment Type",
                options=["A-Roll", "B-Roll"],
                index=0 if segment["type"] == "A-Roll" else 1,
                key=f"type_{i}"
            )
            
            # Change placeholder based on segment type
            if segment_type == "A-Roll":
                placeholder_text = "Enter the script content that will be spoken on camera."
                help_text = "This is the script content that will be spoken in the video."
                
                segment_content = st.text_area(
                    "Content",
                    value=segment["content"],
                    height=100,
                    key=f"content_{i}",
                    placeholder=placeholder_text,
                    help=help_text
                )
            else:  # B-Roll
                placeholder_text = ("Describe the visuals you want to see (not what will be said).\n\n"
                                   "Examples:\n"
                                   "- Slow-motion shot of coffee beans falling into a grinder\n"
                                   "- Aerial view of mountains with morning fog\n"
                                   "- Person walking through busy market with colorful stalls")
                help_text = ("This is NOT spoken content. Describe the visual scene or footage you want to see while the A-Roll audio plays. "
                            "Be specific about visual elements, style, mood, and composition. "
                            "These descriptions will be used to generate detailed prompts in the next step.")
                
                # For B-Roll, add AI generation option
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    segment_content = st.text_area(
                        "Content",
                        value=segment["content"],
                        height=100,
                        key=f"content_{i}",
                        placeholder=placeholder_text,
                        help=help_text
                    )
                
                with col2:
                    st.markdown("### ")  # Add some spacing
                    # Only show AI button if we have models
                    if st.session_state.ollama_models:
                        # Get surrounding A-Roll content for context
                        preceding_content = ""
                        following_content = ""
                        
                        if i > 0 and i-1 < len(st.session_state.segments):
                            preceding_content = st.session_state.segments[i-1].get("content", "")
                        
                        if i+1 < len(st.session_state.segments):
                            following_content = st.session_state.segments[i+1].get("content", "")
                        
                        # Check if using local generator (use same setting as batch generator)
                        use_local = False
                        if 'use_local_generator' in locals() or 'use_local_generator' in globals():
                            use_local = use_local_generator
                        
                        # AI generation button with tooltip based on generator type
                        button_tooltip = "Generate using local generator (no Ollama required)" if use_local else "Generate using Ollama API"
                        button_text = "🤖 Generate Visual" if not use_local else "🔄 Generate Visual (Local)"
                        
                        if st.button(button_text, key=f"gen_broll_{i}", help=button_tooltip):
                            if not use_local and not st.session_state.ollama_models:
                                st.warning("No AI models available. Please refresh the connection.")
                            elif not script_theme:
                                st.warning("Please enter a script theme first.")
                            else:
                                with st.spinner("Generating visual description..."):
                                    # Generate description based on selected method
                                    try:
                                        if use_local:
                                            generated_description = generate_local_description(
                                                preceding_content,
                                                following_content,
                                                script_theme
                                            )
                                        else:
                                            # Use the first available model
                                            model = st.session_state.ollama_models[0]
                                            generated_description = generate_broll_description(
                                                model,
                                                preceding_content,
                                                following_content,
                                                script_theme
                                            )
                                        
                                        # Create a copy of segments
                                        segments_copy = st.session_state.segments.copy()
                                        # Update the specific segment content
                                        segments_copy[i]["content"] = generated_description
                                        # Update session state
                                        st.session_state.segments = segments_copy
                                        # Use rerun to update the UI
                                        st.success("Visual description generated!")
                                        st.experimental_rerun()
                                    except Exception as e:
                                        st.error(f"Error generating description: {str(e)}")
            
            updated_segments.append({
                "type": segment_type,
                "content": segment_content
            })
    
    # Update session state with edited segments
    st.session_state.segments = updated_segments
    
    # Display segment timeline visualization
    st.subheader("Segment Timeline")
    
    timeline_cols = st.columns(len(st.session_state.segments))
    
    for i, (segment, col) in enumerate(zip(st.session_state.segments, timeline_cols)):
        if segment["type"] == "A-Roll":
            col.markdown(f"""
            <div style="background-color:#06d6a0; color:white; padding:10px; border-radius:5px; text-align:center; height:80px;">
            <strong>A-Roll {i+1}</strong>
            </div>
            """, unsafe_allow_html=True)
        else:
            col.markdown(f"""
            <div style="background-color:#118ab2; color:white; padding:10px; border-radius:5px; text-align:center; height:80px;">
            <strong>B-Roll {i+1}</strong>
            </div>
            """, unsafe_allow_html=True)
    
    # Save script and segments
    if st.button("Save Segmentation", type="primary"):
        if script_theme.strip() == "":
            st.error("Please enter a theme for your script before saving.")
        else:
            if save_script_segments(script_text, st.session_state.segments, script_theme):
                st.session_state.script_theme = script_theme
                mark_step_complete("step_2")
                st.success("Script and segments saved successfully!")
else:
    if has_saved_script:
        st.info("Loaded previously saved script. You can make changes and save again.")
    else:
        st.info("Enter your script and click 'Auto-Segment Script' to break it down into A-Roll and B-Roll sections.")

# Display current script theme
if st.session_state.script_theme:
    st.sidebar.markdown("---")
    st.sidebar.subheader("Current Script Theme")
    st.sidebar.info(st.session_state.script_theme)

# Navigation buttons
st.markdown("---")
render_step_navigation(
    current_step=3,
    prev_step_path="pages/2_Blueprint.py",
    next_step_path="pages/4_BRoll_Prompts.py"
) 