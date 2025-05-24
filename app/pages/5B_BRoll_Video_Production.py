import streamlit as st
import os
import sys
import json
import requests
import time
from pathlib import Path
import base64
import threading
from datetime import datetime
import random

# Import custom helper module for ComfyUI integration
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../app"))
import comfyui_helpers

# Fix import paths for components and utilities
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"Added {parent_dir} to path")

# Try to import local modules# Try to import local modules
try:
    from components.custom_navigation import render_custom_sidebar, render_horizontal_navigation, render_step_navigation
    from components.progress import render_step_header
    from utils.session_state import get_settings, get_project_path, mark_step_complete
    from utils.progress_tracker import start_comfyui_tracking
    print("Successfully imported local modules")
except ImportError as e:
    st.error(f"Failed to import local modules: {str(e)}")
    st.stop()
# Set page configuration
st.set_page_config(
    page_title="5B B-Roll Video Production | AI Money Printer",
    page_icon="🎬",
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

# Style for horizontal navigation
st.markdown("""
<style>
    .horizontal-nav {
        margin-bottom: 20px;
        padding: 10px;
        background-color: #f0f2f6;
        border-radius: 10px;
    }
    
    .horizontal-nav button {
        background-color: transparent;
        border: none;
        font-size: 1.2rem;
        margin: 0 5px;
        transition: all 0.3s;
    }
    
    .horizontal-nav button:hover {
        transform: scale(1.2);
    }
</style>
""", unsafe_allow_html=True)

# Add horizontal navigation
st.markdown("<div class='horizontal-nav'>", unsafe_allow_html=True)
render_horizontal_navigation()
st.markdown("</div>", unsafe_allow_html=True)

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
render_custom_sidebar()

# Load settings
settings = get_settings()
project_path = get_project_path()

# Constants
OLLAMA_API_URL = "http://100.115.243.42:11434/api"
COMFYUI_IMAGE_API_URL = "http://100.115.243.42:8000"
COMFYUI_VIDEO_API_URL = "http://100.86.185.76:8000"
JSON_TEMPLATES = {
    "image": {
        "default": "app/image_homepc.json",
        "lora": "app/lora.json",
        "flux": "app/flux_dev_checkpoint.json"
    },
    "video": "app/wan.json"
}

# Initialize session state variables
if "segments" not in st.session_state:
    st.session_state.segments = []
if "broll_prompts" not in st.session_state:
    st.session_state.broll_prompts = {}
if "content_status" not in st.session_state:
    st.session_state.content_status = {
        "broll": {}
    }
if "parallel_tasks" not in st.session_state:
    st.session_state.parallel_tasks = {
        "running": False,
        "completed": 0,
        "total": 0
    }
if "broll_fetch_ids" not in st.session_state:
    # Initialize with default B-Roll IDs
    st.session_state.broll_fetch_ids = {
        "segment_0": "ca26f439-3be6-4897-9e8a-d56448f4bb9a",  # SEG1
        "segment_1": "15027251-6c76-4aee-b5d1-adddfa591257",  # SEG2
        "segment_2": "8f34773a-a113-494b-be8a-e5ecd241a8a4"   # SEG3
    }
if "workflow_selection" not in st.session_state:
    st.session_state.workflow_selection = {
        "image": "default"
    }
if "manual_upload" not in st.session_state:
    st.session_state.manual_upload = False
if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = {}
if "batch_process_status" not in st.session_state:
    st.session_state.batch_process_status = {
        "submitted": False,
        "prompt_ids": {},
        "errors": {}
    }

# Function to load saved script and segments# Function to load saved script and segments (for B-Roll only)
def load_script_data():
    script_file = project_path / "script.json"
    if script_file.exists():
        try:
            with open(script_file, "r") as f:
                data = json.load(f)
                segments = data.get("segments", [])
                
                # Print debug info
                print(f"Debug - Loading script data: Found {len(segments)} segments in script.json")
                
                # Validate segments
                if not segments:
                    print("Warning: No segments found in script.json")
                    return False
                    
                # Count segments by type
                broll_count = sum(1 for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll")
                other_count = len(segments) - broll_count
                
                print(f"Debug - Found {broll_count} B-Roll and {other_count} other segments")
                
                # Only update if we have valid B-Roll segments
                if broll_count > 0:
                    # Filter for B-Roll segments only
                    st.session_state.segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll"]
                    return True
                else:
                    print("Warning: No valid B-Roll segments found in script.json")
                    return False
        except json.JSONDecodeError:
            print("Error: Failed to parse script.json")
            return False
    else:
        print(f"Warning: Script file not found at {script_file}")
        return False
# Function to load saved B-Roll prompts
def load_broll_prompts():
    prompts_file = project_path / "broll_prompts.json"
    if prompts_file.exists():
        try:
            with open(prompts_file, "r") as f:
                data = json.load(f)
                
                # Print debug info
                print(f"Debug - Loading B-Roll prompts from {prompts_file}")
                
                # Validate data structure
                if not isinstance(data, dict):
                    print("Error: B-Roll prompts file has invalid format")
                    return False
                
                # Handle different JSON structures
                if "prompts" in data and isinstance(data["prompts"], dict):
                    # New format: {"prompts": {"segment_0": {...}, ...}, "broll_type": "..."}
                    prompts_data = data["prompts"]
                    broll_type = data.get("broll_type", "video")
                    
                    # Count prompts
                    prompt_count = sum(1 for segment_id, prompt_data in prompts_data.items() 
                                     if isinstance(prompt_data, dict) and "prompt" in prompt_data)
                    
                    print(f"Debug - Found {prompt_count} B-Roll prompts")
                    
                    # Update session state if we have valid prompts
                    if prompt_count > 0:
                        st.session_state.broll_prompts = prompts_data
                        st.session_state.broll_type = broll_type
                        return True
                else:
                    # Legacy format: {"segment_0": {...}, ...}
                    # Count prompts
                    prompt_count = sum(1 for segment_id, prompt_data in data.items() 
                                     if isinstance(prompt_data, dict) and "prompt" in prompt_data)
                    
                    print(f"Debug - Found {prompt_count} B-Roll prompts")
                    
                    # Update session state if we have valid prompts
                    if prompt_count > 0:
                        st.session_state.broll_prompts = data
                        return True
                
                print("Warning: No valid B-Roll prompts found")
                return False
        except json.JSONDecodeError:
            print(f"Error: broll_prompts.json is not valid JSON")
            return False
        except Exception as e:
            print(f"Error loading B-Roll prompts: {str(e)}")
            return False
    else:
        print(f"B-Roll prompts file not found at: {prompts_file}")
        return False
# Function to load content status
def load_content_status():
    status_file = project_path / "content_status.json"
    if status_file.exists():
        try:
            with open(status_file, "r") as f:
                content_status = json.load(f)
                st.session_state.content_status = content_status
                
                # Also update broll_fetch_ids from content_status
                if "broll" in content_status:
                    for segment_id, segment_data in content_status["broll"].items():
                        if "prompt_id" in segment_data:
                            if "broll_fetch_ids" not in st.session_state:
                                st.session_state.broll_fetch_ids = {}
                            st.session_state.broll_fetch_ids[segment_id] = segment_data["prompt_id"]
                
            return True
        except json.JSONDecodeError:
            st.warning("Content status file exists but contains invalid JSON. Creating a new one.")
            # Initialize with default values
            st.session_state.content_status = {"broll": {}}
            save_content_status()
            return False
        except Exception as e:
            st.error(f"Error loading content status: {str(e)}")
            return False
    return False
# Function to save content status
def save_content_status():
    status_file = project_path / "content_status.json"
    with open(status_file, "w") as f:
        json.dump(st.session_state.content_status, f, indent=4)
    return True

# Function to replace template values in ComfyUI workflow JSON
def prepare_comfyui_workflow(template_file, prompt, negative_prompt, resolution="1080x1920"):
    try:
        # Load the template workflow
        with open(template_file, "r") as f:
            workflow = json.load(f)
        
        # Extract width and height from resolution
        width, height = map(int, resolution.split("x"))
        
        # Modify the workflow with our prompt and resolution
        # This depends on the specific structure of your workflow templates
        # The actual node IDs and parameter names will vary
        for node_id, node in workflow.items():
            if "inputs" in node:
                if "prompt" in node["inputs"]:
                    node["inputs"]["prompt"] = prompt
                if "negative" in node["inputs"]:
                    node["inputs"]["negative"] = negative_prompt
                if "text" in node["inputs"] and "CLIPTextEncode" in node.get("class_type", ""):
                    # Check for positive/negative prompt encoding nodes
                    if "Positive" in node.get("_meta", {}).get("title", ""):
                        node["inputs"]["text"] = prompt
                    elif "Negative" in node.get("_meta", {}).get("title", ""):
                        node["inputs"]["text"] = negative_prompt
                if "width" in node["inputs"]:
                    node["inputs"]["width"] = width
                if "height" in node["inputs"]:
                    node["inputs"]["height"] = height
        
        return workflow
    except FileNotFoundError:
        st.error(f"Error: Workflow template file not found: {template_file}")
        return None
    except json.JSONDecodeError:
        st.error(f"Error: Invalid JSON in workflow template: {template_file}")
        return None
    except Exception as e:
        st.error(f"Error preparing workflow: {str(e)}")
        return None

# Function to submit job to ComfyUI
def submit_comfyui_job(api_url, workflow):
    """
    Submit a job to ComfyUI
    """
    try:
        # Use the correct ComfyUI server URL
        api_url = "http://100.115.243.42:8000"
        print(f"Submitting job to ComfyUI at: {api_url}")
        
        response = requests.post(f"{api_url}/prompt", json=workflow, timeout=30)
        if response.status_code == 200:
            result = response.json()
            print(f"Job submitted successfully. Response: {result}")
            return result
        else:
            print(f"Error submitting job. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error submitting job: {str(e)}")
        return None

# Function to check ComfyUI job status
def check_comfyui_job_status(api_url, prompt_id):
    """
    Check the status of a ComfyUI job
    """
    try:
        # Use the correct ComfyUI server URL
        api_url = "http://100.115.243.42:8000"
        print(f"Checking job status at: {api_url}/history/{prompt_id}")
        
        response = requests.get(f"{api_url}/history/{prompt_id}", timeout=30)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error checking job status. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error checking job status: {str(e)}")
        return None

# Function to get file from ComfyUI node
def get_comfyui_file(api_url, filename, node_id=""):
    try:
        # ComfyUI uses /view endpoint for files
        file_url = f"{api_url}/view?filename={filename}"
        
        # Get the file
        response = requests.get(file_url)
        
        if response.status_code == 200:
            return response.content
        else:
            st.error(f"Error getting file: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error downloading file: {str(e)}")
        return None

# Function to fetch ComfyUI job history
def fetch_comfyui_job_history(api_url, limit=20):
    """Fetch recent job history from ComfyUI API
    
    Args:
        api_url: URL to the ComfyUI API
        limit: Maximum number of history items to return
        
    Returns:
        A list of job history items (prompt_id, timestamp, status)
    """
    try:
        # ComfyUI stores history at /history endpoint
        response = requests.get(f"{api_url}/history", timeout=10)
        
        if response.status_code != 200:
            return {"status": "error", "message": f"Error fetching history: {response.status_code}"}
            
        data = response.json()
        
        # Debug the API response format
        print(f"ComfyUI API response type: {type(data)}")
        
        # Process the history data - handle both dict and list response formats
        history_items = []
        
        # If data is a list (newer ComfyUI versions may return a list)
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "prompt_id" in item:
                    # Extract data from list format
                    prompt_id = item.get("prompt_id", "unknown")
                    timestamp = item.get("created_at", "Unknown")
                    status = item.get("status", "Unknown")
                    
                    # Try to get prompt text if available
                    prompt_text = ""
                    outputs = {}
                    
                    history_items.append({
                        "prompt_id": prompt_id,
                        "timestamp": timestamp,
                        "status": status,
                        "prompt_text": prompt_text,
                        "outputs": outputs
                    })
        # If data is a dictionary (traditional ComfyUI format)
        elif isinstance(data, dict):
            for prompt_id, job_info in data.items():
                # Skip if job_info is not a dictionary
                if not isinstance(job_info, dict):
                    continue
                    
                # Extract timestamp if available
                timestamp = "Unknown"
                if "prompt" in job_info and isinstance(job_info["prompt"], dict):
                    if "extra_data" in job_info["prompt"] and isinstance(job_info["prompt"]["extra_data"], dict):
                        extra_data = job_info["prompt"]["extra_data"]
                        if "datetime" in extra_data:
                            timestamp = extra_data["datetime"]
                
                # Determine job status
                status = "Unknown"
                if "status" in job_info and isinstance(job_info["status"], dict):
                    if "status_str" in job_info["status"]:
                        status = job_info["status"]["status_str"]
                    elif "completed" in job_info["status"] and job_info["status"]["completed"] == True:
                        status = "success"
                            
                # Extract prompt text if available
                prompt_text = ""
                outputs = {}
                if "outputs" in job_info and isinstance(job_info["outputs"], dict):
                    outputs = job_info["outputs"]
                
                # Get first part of prompt from any text encode node
                if "prompt" in job_info and isinstance(job_info["prompt"], dict) and "nodes" in job_info["prompt"]:
                    nodes = job_info["prompt"]["nodes"]
                    if isinstance(nodes, dict):
                        for node_id, node_data in nodes.items():
                            if isinstance(node_data, dict) and node_data.get("class_type", "") == "CLIPTextEncode" and "inputs" in node_data:
                                if "text" in node_data["inputs"] and "Negative" not in node_data.get("_meta", {}).get("title", ""):
                                    prompt_text = node_data["inputs"]["text"]
                                    if len(prompt_text) > 80:
                                        prompt_text = prompt_text[:77] + "..."
                                    break
                
                # Add to history items
                history_items.append({
                    "prompt_id": prompt_id,
                    "timestamp": timestamp,
                    "status": status,
                    "prompt_text": prompt_text,
                    "outputs": outputs
                })
        else:
            return {"status": "error", "message": f"Unexpected response format from ComfyUI API: {type(data)}"}
        
        # Sort by timestamp (newest first) and limit number of items
        # Use a safer sorting approach that handles missing or invalid timestamps
        try:
            history_items.sort(key=lambda x: x["timestamp"], reverse=True)
        except Exception as sort_error:
            print(f"Warning: Could not sort history items: {str(sort_error)}")
            
        if limit > 0 and len(history_items) > limit:
            history_items = history_items[:limit]
            
        return {"status": "success", "data": history_items}
    
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Timeout while fetching job history"}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": f"Could not connect to ComfyUI API at {api_url}"}
    except Exception as e:
        return {"status": "error", "message": f"Error fetching job history: {str(e)}"}

# Function to fetch content by ID from ComfyUI
def fetch_comfyui_content_by_id(api_url, prompt_id, max_retries=3, retry_delay=5):
    """
    Fetch content by ID from ComfyUI with retry logic
    """
    # Use the correct ComfyUI server URL
    api_url = "http://100.115.243.42:8000"
    print(f"\n=== Fetching content for prompt_id: {prompt_id} ===")
    print(f"API URL: {api_url}")
    
    def make_request(url, method='get', timeout=60, **kwargs):
        """Helper function to make requests with retry logic"""
        for attempt in range(max_retries):
            try:
                print(f"Attempt {attempt + 1}/{max_retries} for {url}")
                if method.lower() == 'get':
                    response = requests.get(url, timeout=timeout, **kwargs)
                elif method.lower() == 'head':
                    response = requests.head(url, timeout=timeout, **kwargs)
                return response
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    print(f"Timeout on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise
            except requests.exceptions.ConnectionError:
                if attempt < max_retries - 1:
                    print(f"Connection error on attempt {attempt + 1}, retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    raise
    
    try:
        # First check if the job exists in history
        history_url = f"{api_url}/history/{prompt_id}"
        print(f"\n1. Checking history at: {history_url}")
        
        history_response = make_request(history_url, timeout=60)
        print(f"History response status: {history_response.status_code}")
        
        if history_response.status_code != 200:
            error_msg = f"Error fetching history: {history_response.status_code}. Server might be busy, try again later."
            print(error_msg)
            return {"status": "error", "message": error_msg}
            
        job_data = history_response.json()
        print(f"Job data keys: {list(job_data.keys())}")
        
        if prompt_id not in job_data:
            error_msg = f"Prompt ID '{prompt_id}' not found in history. The job may have been deleted or hasn't been submitted yet."
            print(error_msg)
            st.warning(error_msg)
            return {"status": "error", "message": "Prompt ID not found in history"}
            
        # Get the job data
        job_info = job_data[prompt_id]
        print(f"\n2. Job info keys: {list(job_info.keys())}")
        
        # Check if job has outputs
        if "outputs" in job_info and job_info["outputs"]:
            outputs = job_info["outputs"]
            print(f"\n3. Output nodes: {list(outputs.keys())}")
            
            # Iterate through output nodes to find image/video output
            for node_id, node_data in outputs.items():
                print(f"\n4. Processing node: {node_id}")
                print(f"Node data keys: {list(node_data.keys())}")
                
                # Check for images
                if "images" in node_data:
                    print(f"Found {len(node_data['images'])} images")
                    for image_data in node_data["images"]:
                        filename = image_data["filename"]
                        file_type = image_data.get("type", "image")
                        print(f"Processing image: {filename} (type: {file_type})")
                        
                        # Download the file
                        file_url = f"{api_url}/view?filename={filename}"
                        print(f"Downloading from: {file_url}")
                        
                        content_response = make_request(file_url, timeout=120)
                        if content_response.status_code == 200:
                            print(f"Successfully downloaded image: {filename}")
                            return {
                                "status": "success",
                                "content": content_response.content,
                                "filename": filename,
                                "prompt_id": prompt_id,
                                "type": file_type
                            }
                        else:
                            print(f"Failed to download image. Status code: {content_response.status_code}")
                
                # Check for videos and other media files
                for media_type in ["videos", "gifs", "mp4"]:
                    if media_type in node_data:
                        print(f"Found {len(node_data[media_type])} {media_type}")
                        for media_item in node_data[media_type]:
                            filename = media_item.get("filename", "")
                            if filename:
                                # Determine actual file type from extension
                                file_ext = os.path.splitext(filename)[1].lower()
                                actual_type = "video" if file_ext == ".mp4" else media_type
                                
                                print(f"Processing {actual_type}: {filename}")
                                
                                # Download the file
                                file_url = f"{api_url}/view?filename={filename}"
                                print(f"Downloading from: {file_url}")
                                
                                content_response = make_request(file_url, timeout=180)
                                if content_response.status_code == 200:
                                    print(f"Successfully downloaded {actual_type}: {filename}")
                                    return {
                                        "status": "success",
                                        "content": content_response.content,
                                        "filename": filename,
                                        "prompt_id": prompt_id,
                                        "type": actual_type
                                    }
                                else:
                                    print(f"Failed to download {actual_type}. Status code: {content_response.status_code}")
            
            # Check for AnimateDiff outputs
            print("\n5. Checking for AnimateDiff outputs")
            possible_files = [f"animation_{i:05d}.mp4" for i in range(1, 10)]
            for filename in possible_files:
                try:
                    file_url = f"{api_url}/view?filename={filename}"
                    print(f"Checking: {file_url}")
                    
                    response = make_request(file_url, method='head', timeout=30)
                    if response.status_code == 200:
                        print(f"Found AnimateDiff file: {filename}")
                        content_response = make_request(file_url, timeout=180)
                        if content_response.status_code == 200:
                            print(f"Successfully downloaded AnimateDiff output: {filename}")
                            return {
                                "status": "success",
                                "content": content_response.content,
                                "filename": filename,
                                "prompt_id": prompt_id,
                                "type": "video",
                                "note": "Found using filename pattern"
                            }
                except Exception as e:
                    print(f"Error checking AnimateDiff file {filename}: {str(e)}")
            
            # If we got here, we couldn't find any output files
            error_msg = "No output file found in job results"
            print(error_msg)
            return {"status": "error", "message": error_msg}
        else:
            # Job is still processing
            status_msg = "Job is still processing"
            print(status_msg)
            return {"status": "processing", "message": status_msg}
            
    except requests.exceptions.Timeout as e:
        error_msg = f"Timeout while fetching content after {max_retries} attempts. The server may be busy. Error: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Could not connect to ComfyUI API at {api_url} after {max_retries} attempts. The server might be down. Error: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}
    except Exception as e:
        error_msg = f"Error fetching content: {str(e)}"
        print(error_msg)
        return {"status": "error", "message": error_msg}

# Function to save media content to file
def save_media_content(content, segment_type, segment_id, file_extension):
    # Create directories if they don't exist
    media_dir = project_path / "media" / segment_type
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{segment_type}_{segment_id}_{timestamp}.{file_extension}"
    
    # Save file
    file_path = media_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Return relative path from project directory
    return str(file_path)

# Function for batch processing prompts
def batch_process_broll_prompts():
    """Submit all B-Roll prompts to the video server for processing"""
    broll_segments = [s for s in st.session_state.segments if s["type"] == "B-Roll"]
    prompt_ids = {}
    errors = {}
    
    # Reset batch process status
    st.session_state.batch_process_status["submitted"] = True
    st.session_state.batch_process_status["prompt_ids"] = {}
    st.session_state.batch_process_status["errors"] = {}
    
    # Get the workflow template path for video
    template_file = JSON_TEMPLATES["video"]
    
    # Process each B-Roll segment
    for i, segment in enumerate(broll_segments):
        segment_id = f"segment_{i}"
        
        # Check if we have prompts for this segment
        if "prompts" in st.session_state.broll_prompts and segment_id in st.session_state.broll_prompts["prompts"]:
            prompt_data = st.session_state.broll_prompts["prompts"][segment_id]
            
            # Prepare the workflow
            workflow = prepare_comfyui_workflow(
                template_file,
                prompt_data["prompt"],
                prompt_data.get("negative_prompt", "ugly, blurry, low quality"),
                resolution="1080x1920"
            )
            
            if workflow:
                # Submit to ComfyUI
                prompt_id = submit_comfyui_job(COMFYUI_VIDEO_API_URL, workflow)
                
                if prompt_id:
                    prompt_ids[segment_id] = prompt_id
                    
                    # Save the prompt ID for later reference
                    st.session_state.broll_fetch_ids[segment_id] = prompt_id
                    
                    # Set up progress tracking
                    tracker = start_comfyui_tracking(prompt_id, COMFYUI_VIDEO_API_URL)
                    if "active_trackers" not in st.session_state:
                        st.session_state.active_trackers = []
                    st.session_state.active_trackers.append(tracker)
                    
                    # Update content status
                    st.session_state.content_status["broll"][segment_id] = {
                        "status": "processing",
                        "prompt_id": prompt_id,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                else:
                    errors[segment_id] = "Failed to submit job to ComfyUI"
            else:
                errors[segment_id] = "Failed to prepare workflow"
        else:
            errors[segment_id] = "No prompt data found for this segment"
    
    # Save the results to session state
    st.session_state.batch_process_status["prompt_ids"] = prompt_ids
    st.session_state.batch_process_status["errors"] = errors
    
    # Save content status to file
    save_content_status()
    
    # Force refresh of UI by triggering a rerun after a short delay
    if prompt_ids:
        st.success(f"Successfully generated {len(prompt_ids)} new jobs. UI will update with new IDs...")
        time.sleep(0.5)
        st.rerun()
    
    return prompt_ids, errors

# Function for A-Roll content generation only
def generate_aroll_content(segments, aroll_fetch_ids):
    """Generate A-Roll content only - DISABLED: Use 5A_ARoll_Video_Production.py instead"""
    # This function is disabled - A-Roll generation should be done in the dedicated 5A page
    st.warning("⚠️ A-Roll generation is disabled in this page. Please use the '5A A-Roll Video Production' page instead.")
    
    # Mark as complete immediately to avoid issues
    if "parallel_tasks" in st.session_state:
        st.session_state.parallel_tasks["completed"] = 1
        st.session_state.parallel_tasks["running"] = False
        
    return {
                            "status": "error",
        "message": "A-Roll generation is disabled in this page. Please use the '5A A-Roll Video Production' page instead."
    }

# Function for parallel content generation
def generate_content_parallel(segments, broll_prompts, manual_upload, broll_fetch_ids, workflow_selection):
    """
    Generate B-Roll content for all segments, either through API or manual upload
    
    Args:
        segments: List of segments to generate B-Roll for
        broll_prompts: Dictionary of B-Roll prompts
        manual_upload: Whether to use manual upload
        broll_fetch_ids: IDs of B-Roll videos to fetch (if manual upload)
        workflow_selection: ComfyUI workflow selection
        
    Returns:
        dict: Status of content generation
    """
    # Only generate for B-Roll segments
    broll_segments = [s for s in segments if s.get("type") == "B-Roll"]
    
    if not broll_segments:
        st.warning("No B-Roll segments found. Please complete the Script Segmentation step first.")
        return {
            "status": "error",
            "message": "No B-Roll segments found"
        }
        
    # Initialize result
    result = {
        "status": "success",
        "generated": 0,
        "errors": {}
    }
    
    # Generate B-Roll content
    try:
        broll_result = generate_broll_content(
            broll_segments, 
            broll_prompts, 
            broll_fetch_ids, 
            workflow_selection
        )
        
        if "status" in broll_result and broll_result["status"] == "success":
            result["generated"] += broll_result.get("generated", 0)
            result["broll"] = broll_result
        else:
            result["errors"]["broll"] = broll_result.get("message", "Unknown error")
    except Exception as e:
        result["errors"]["broll"] = str(e)
    
    # Return overall results
    if result["errors"]:
        result["status"] = "partial"
        result["message"] = f"Completed with {len(result['errors'])} errors"
    
    if result["generated"] == 0 and result["errors"]:
        result["status"] = "error"
        result["message"] = "Failed to generate any content"
    
    return result

# Page header
render_step_header(
    title="5B B-Roll Video Production",
    description="Generate B-Roll videos using ComfyUI",
    icon="🎬"
)

# Add a strong visual alert about cache issues
st.error("""
## ⚠️ IMPORTANT: CLEAR CACHE ⚠️
If you're seeing old B-Roll IDs in the input fields, click the "CLEAR ALL CACHE" button below. 
This is a known issue with Streamlit's caching mechanism.
""")

# Add a clear cache button with more emphasis
if st.button("🔄 CLEAR ALL CACHE", type="primary", key="force_clear_cache", help="Completely reset all cache", use_container_width=True):
    # Perform a complete wipe of session state
    for key in list(st.session_state.keys()):
        if key.startswith("broll_") or "content_status" in key:
            del st.session_state[key]
    
    # Force reset broll_fetch_ids
    st.session_state.broll_fetch_ids = {
        "segment_0": "ca26f439-3be6-4897-9e8a-d56448f4bb9a",
        "segment_1": "15027251-6c76-4aee-b5d1-adddfa591257", 
        "segment_2": "8f34773a-a113-494b-be8a-e5ecd241a8a4"
    }
    
    # Also refresh content status from file
    status_file = project_path / "content_status.json"
    if status_file.exists():
        with open(status_file, "r") as f:
            st.session_state.content_status = json.load(f)
    
    # Show success and rerun
    st.success("Cache cleared! Reloading page...")
    time.sleep(1)
    st.rerun()

st.title("⚡ B-Roll Content Production")
st.markdown("""
This page is for generating visual B-Roll content only. For A-Roll (talking head) production, please use the '5A A-Roll Video Production' page.

This step will use the prompts generated in the previous step to create all the visual B-Roll assets for your video.
""")

# Add a clear cache button
clear_cache_col1, clear_cache_col2 = st.columns([3, 1])
with clear_cache_col1:
    st.warning("**⚠️ If you see old B-Roll IDs in the input fields below, click the 'Reset B-Roll IDs' button →**")
    
with clear_cache_col2:
    if st.button("🔄 Reset B-Roll IDs", key="clear_cache_button", type="primary", help="Completely reset the B-Roll IDs to use the new values"):
        # Force complete reset
        if "content_status" in st.session_state:
            del st.session_state.content_status
        
        # Recreate broll_fetch_ids with the new IDs
        st.session_state.broll_fetch_ids = {
            "segment_0": "ca26f439-3be6-4897-9e8a-d56448f4bb9a",  # SEG1
            "segment_1": "15027251-6c76-4aee-b5d1-adddfa591257",  # SEG2
            "segment_2": "8f34773a-a113-494b-be8a-e5ecd241a8a4"   # SEG3
        }
        
        # Clear any keys that might have the old B-roll IDs cached
        keys_to_delete = []
        for key in st.session_state:
            if key.startswith("broll_id_segment_"):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del st.session_state[key]
            
        # Force the page to reload
        st.success("B-Roll IDs reset successfully! Reloading page...")
        time.sleep(1)
        st.rerun()

# Load required data
has_script = load_script_data()
has_prompts = load_broll_prompts()
_ = load_content_status()  # Load if exists, but no need to check return value

# Check for required data and provide clear guidance
if not has_script:
    st.error("No script segments found. Please complete the Script Segmentation step (Step 3) first.")
    with st.expander("How to create script segments"):
        st.markdown("""
        ### How to create script segments:
        1. Go to the **Script Segmentation** page (Step 3)
        2. Enter your script or generate one
        3. Segment the script into A-Roll (on-camera) and B-Roll (visual) segments
        4. Save your segmented script
        """)
    st.button("Go to Script Segmentation", on_click=lambda: st.switch_page("pages/3_Script_Segmentation.py"))
    st.stop()

if not has_prompts:
    st.error("No B-Roll prompts found. Please complete the B-Roll Prompt Generation step (Step 4) first.")
    with st.expander("How to generate B-Roll prompts"):
        st.markdown("""
        ### How to generate B-Roll prompts:
        1. Go to the **B-Roll Prompts** page (Step 4)
        2. Select your prompt generation style
        3. Generate prompts for each B-Roll segment
        4. Save your prompts
        """)
    st.button("Go to B-Roll Prompts", on_click=lambda: st.switch_page("pages/4_BRoll_Prompts.py"))
    st.stop()

# Verify segments are properly loaded and formatted
if not st.session_state.segments or len(st.session_state.segments) == 0:
    st.error("Script segments were loaded but appear to be empty. Please go back and complete the Script Segmentation step properly.")
    st.button("Go to Script Segmentation", on_click=lambda: st.switch_page("pages/3_Script_Segmentation.py"))
    st.stop()

# Count segments by type for verification
aroll_segments = [s for s in st.session_state.segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
broll_segments = [s for s in st.session_state.segments if isinstance(s, dict) and s.get("type") == "B-Roll"]

if len(aroll_segments) == 0 and len(broll_segments) == 0:
    st.error("Script segments were loaded but don't have proper type information (A-Roll/B-Roll). Please go back and complete the Script Segmentation step properly.")
    st.button("Go to Script Segmentation", on_click=lambda: st.switch_page("pages/3_Script_Segmentation.py"))
    st.stop()

# Show production options
st.subheader("Content Production Options")

# Add ComfyUI job history section
st.markdown("---")
st.subheader("🔍 ComfyUI Job History")
st.markdown("Fetch recent job IDs from ComfyUI to reuse existing content.")

fetch_col1, fetch_col2 = st.columns([3, 1])

with fetch_col1:
    api_selection = st.radio(
        "Select ComfyUI API:",
        options=["Image API", "Video API"],
        horizontal=True,
        key="comfyui_api_selection"
    )
    api_url = COMFYUI_IMAGE_API_URL if api_selection == "Image API" else COMFYUI_VIDEO_API_URL
    
with fetch_col2:
    history_limit = st.number_input("Max results:", min_value=5, max_value=50, value=20, step=5)
    fetch_button = st.button("🔄 Fetch Job History", type="primary", use_container_width=True)

# Initialize job history in session state if not present
if "comfyui_job_history" not in st.session_state:
    st.session_state.comfyui_job_history = {"image": [], "video": []}

# Handle fetch button click
if fetch_button:
    with st.spinner(f"Fetching job history from {api_selection}..."):
        api_key = "image" if api_selection == "Image API" else "video"
        result = fetch_comfyui_job_history(api_url, limit=history_limit)
        
        if result["status"] == "success":
            st.session_state.comfyui_job_history[api_key] = result["data"]
            st.success(f"Successfully fetched {len(result['data'])} jobs from {api_selection}")
        else:
            st.error(f"Error fetching job history: {result.get('message', 'Unknown error')}")

# Display job history
api_key = "image" if api_selection == "Image API" else "video"
if api_key in st.session_state.comfyui_job_history and st.session_state.comfyui_job_history[api_key]:
    # Add tabs for different view options
    history_tab1, history_tab2 = st.tabs(["Table View", "Detail View"])
    
    with history_tab1:
        # Create a dataframe from job history
        job_data = []
        for job in st.session_state.comfyui_job_history[api_key]:
            job_data.append({
                "Prompt ID": job["prompt_id"],
                "Status": job["status"],
                "Time": job["timestamp"],
                "Prompt": job["prompt_text"]
            })
        
        # Display as a dataframe
        st.dataframe(job_data, use_container_width=True)
    
    with history_tab2:
        # Show jobs with more details and copy buttons
        for i, job in enumerate(st.session_state.comfyui_job_history[api_key]):
            with st.expander(f"Job {i+1}: {job['prompt_id'][:10]}...", expanded=i==0):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"**Prompt ID:** {job['prompt_id']}")
                    st.markdown(f"**Status:** {job['status']}")
                    st.markdown(f"**Timestamp:** {job['timestamp']}")
                    if job['prompt_text']:
                        st.markdown(f"**Prompt:** {job['prompt_text']}")
                
                with col2:
                    # Add copy to clipboard button (uses JavaScript)
                    st.markdown(
                        f"""
                        <button 
                            onclick="navigator.clipboard.writeText('{job['prompt_id']}');alert('Copied ID to clipboard!');" 
                            style="background-color:#4CAF50;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer;width:100%;">
                            📋 Copy ID
                        </button>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    # Add button to directly apply this ID
                    if st.button(f"Apply ID", key=f"apply_btn_{i}", use_container_width=True):
                        st.session_state.selected_prompt_id = job['prompt_id']
                        st.rerun()
                
                # Show outputs if available
                if job['outputs']:
                    st.markdown("**Outputs:**")
                    # Extract output node info
                    for node_id, output in job['outputs'].items():
                        if "images" in output:
                            for img in output["images"]:
                                st.markdown(f"- {img.get('filename', 'Unknown file')}")
                        elif "gifs" in output or "videos" in output:
                            media = output.get("videos", output.get("gifs", []))
                            for vid in media:
                                st.markdown(f"- {vid.get('filename', 'Unknown file')}")
    
    # Add a section to apply selected ID to segments
    st.markdown("### Apply Selected ID to Segments")
    st.markdown("Select a prompt ID from above and apply it to a specific segment.")
    
    # Prompt ID input with improved default
    default_id = st.session_state.get("selected_prompt_id", "")
    prompt_id = st.text_input("Enter Prompt ID:", value=default_id, key="prompt_id_input")
    
    # Select segment type
    segment_type = st.radio("Select segment type:", ["A-Roll", "B-Roll"], horizontal=True)
    
    # Get segments of selected type
    segments = [s for s in st.session_state.segments if isinstance(s, dict) and s.get("type") == segment_type]
    segment_options = [f"Segment {i+1}: {s.get('content', '')[:50]}..." for i, s in enumerate(segments)]
    
    if segment_options:
        selected_segment = st.selectbox("Select segment to apply ID:", options=segment_options)
        segment_index = segment_options.index(selected_segment)
        
        if st.button("Apply ID to Selected Segment", type="primary"):
            segment_id = f"segment_{segment_index}"
            if segment_type == "A-Roll":
                st.session_state.aroll_fetch_ids[segment_id] = prompt_id
            else:
                st.session_state.broll_fetch_ids[segment_id] = prompt_id
            
            st.success(f"Applied prompt ID {prompt_id} to {segment_type} {segment_id}")
            st.rerun()
    else:
        st.warning(f"No {segment_type} segments found. Please complete the Script Segmentation step first.")
else:
    st.info(f"No job history fetched yet from {api_selection}. Click 'Fetch Job History' to retrieve job IDs.")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### A-Roll Options")
    st.info("A-Roll segments are the parts where you appear on camera.")
    st.markdown("For this prototype, A-Roll generation is simulated.")
    
    # A-Roll ID fetch inputs
    st.markdown("##### Fetch Existing A-Roll by ID")
    st.caption("Optional: Enter IDs to use existing A-Roll content")
    
    for i, segment in enumerate(aroll_segments):
        segment_id = f"segment_{i}"
        fetch_id = st.text_input(
            f"A-Roll ID for Segment {i+1}",
            value=st.session_state.aroll_fetch_ids.get(segment_id, ""),
            key=f"aroll_id_{segment_id}"
        )
        st.session_state.aroll_fetch_ids[segment_id] = fetch_id

with col2:
    st.markdown("#### B-Roll Options")
    broll_type = st.session_state.broll_prompts.get("broll_type", "mixed")
    st.info(f"B-Roll type: **{broll_type}**")
    
    # Add workflow selection for image generation
    st.markdown("##### ComfyUI Workflow Selection")
    workflow_options = {
        "default": "Default Image Workflow (image_homepc.json)",
        "lora": "LoRA Enhanced Workflow (lora.json)",
        "flux": "Flux Dev Checkpoint (flux_dev_checkpoint.json)"
    }
    
    selected_workflow = st.selectbox(
        "Select workflow for image generation:",
        options=list(workflow_options.keys()),
        format_func=lambda x: workflow_options[x],
        index=list(workflow_options.keys()).index(st.session_state.workflow_selection["image"]),
        key="workflow_selector"
    )
    st.session_state.workflow_selection["image"] = selected_workflow
    
    # Show info about the selected workflow
    if selected_workflow == "default":
        st.info("Default workflow using standard Stable Diffusion image generation.")
    elif selected_workflow == "lora":
        st.info("LoRA workflow adds the flux-chatgpt-ghibli-lora for stylized image generation.")
    elif selected_workflow == "flux":
        st.info("Flux Dev Checkpoint workflow uses newer Flux models which may better handle complex prompts.")
    
    # Add note about video generation
    st.caption("Note: Video generation always uses the standard video workflow (wan.json)")
    
    # Add manual upload option
    st.markdown("##### Content Generation Method")
    manual_upload = st.radio(
        "How would you like to handle B-Roll content?",
        options=["Automatic Generation", "Manual Upload"],
        index=1 if st.session_state.manual_upload else 0,
        key="manual_upload_radio"
    )
    st.session_state.manual_upload = (manual_upload == "Manual Upload")
    
    if st.session_state.manual_upload:
        st.info("You've selected manual upload. You can upload your own B-Roll content or batch process prompts to download later.")
        
        batch_col1, batch_col2 = st.columns([2,1])
        
        with batch_col1:
            # Add information about batch processing
            st.markdown("##### Batch Process B-Roll Prompts")
            st.markdown("""
            Submit all B-Roll prompts to the video server for processing. This will:
            - Send all prompts to the ComfyUI Video Server
            - Track job progress for each segment
            - Allow you to fetch the generated content later
            """)
        
        with batch_col2:
            # Add button to batch process all prompts
            if st.button("🚀 Submit All B-Roll Prompts", type="primary", use_container_width=True):
                with st.spinner("Submitting prompts to video server..."):
                    prompt_ids, errors = batch_process_broll_prompts()
                    if prompt_ids:
                        st.success(f"Successfully submitted {len(prompt_ids)} prompts to video server!")
                    if errors:
                        st.error(f"Encountered {len(errors)} errors during submission.")
                    st.rerun()
        
        # Display batch process status
        if st.session_state.batch_process_status["submitted"]:
            st.markdown("##### Batch Submission Results")
            prompt_ids = st.session_state.batch_process_status["prompt_ids"]
            errors = st.session_state.batch_process_status["errors"]
            
            tab1, tab2 = st.tabs(["Submitted Jobs", "Errors"])
            
            with tab1:
                if prompt_ids:
                    st.success(f"Successfully submitted {len(prompt_ids)} jobs to the video server")
                    
                    # Create a table of job IDs
                    job_data = []
                    for segment_id, prompt_id in prompt_ids.items():
                        segment_num = segment_id.split('_')[1]
                        
                        # Get the prompt text if available
                        prompt_text = "No prompt available"
                        if "prompts" in st.session_state.broll_prompts and segment_id in st.session_state.broll_prompts["prompts"]:
                            prompt_text = st.session_state.broll_prompts["prompts"][segment_id].get("prompt", "No prompt available")
                            if len(prompt_text) > 50:
                                prompt_text = prompt_text[:50] + "..."
                                
                        job_data.append({
                            "Segment": f"Segment {segment_num}",
                            "Prompt ID": prompt_id,
                            "Prompt": prompt_text
                        })
                    
                    # Display as a dataframe
                    st.dataframe(job_data, use_container_width=True)
                    
                    # Add a note about how to use these IDs
                    st.info("These prompt IDs can be used to fetch the generated content later. You can copy them for future reference.")
                    
                    # Add a check status button
                    if st.button("🔄 Check Job Status", key="check_batch_status"):
                        st.info("This would check the status of all submitted jobs. This feature is still under development.")
                else:
                    st.info("No jobs were submitted successfully.")
            
            with tab2:
                if errors:
                    st.error(f"Encountered {len(errors)} errors during submission")
                    
                    # Create a table of errors
                    error_data = []
                    for segment_id, error_msg in errors.items():
                        segment_num = segment_id.split('_')[1]
                        error_data.append({
                            "Segment": f"Segment {segment_num}",
                            "Error": error_msg
                        })
                    
                    # Display as a dataframe
                    st.dataframe(error_data, use_container_width=True)
                else:
                    st.success("No errors encountered during batch submission.")
    else:
        # B-Roll ID fetch inputs when not using manual upload
        st.markdown("##### Fetch Existing B-Roll by ID")
        st.markdown("""
        <style>
        .stTextInput > div > div > input {
            background-color: #f0f8ff;
        }
        </style>
        """, unsafe_allow_html=True)
        
        # Force cache invalidation warning
        st.warning("⚠️ **IMPORTANT**: If you still see old IDs below, please clear your browser cache and refresh the page.")
        
        # Completely new implementation using unique IDs
        broll_ids = {}
        # Default IDs for the first 3 segments
        default_ids = {
            "segment_0": "ca26f439-3be6-4897-9e8a-d56448f4bb9a",
            "segment_1": "15027251-6c76-4aee-b5d1-adddfa591257", 
            "segment_2": "8f34773a-a113-494b-be8a-e5ecd241a8a4"
        }
        
        # Ensure broll_ids has entries for all segments
        for i, segment in enumerate(broll_segments):
            segment_id = f"segment_{i}"
            # First try to get from session state, then from defaults, then empty string
            broll_ids[segment_id] = st.session_state.broll_fetch_ids.get(
                segment_id, 
                default_ids.get(segment_id, "")
            )
        
        # Use current timestamp for truly unique keys
        timestamp = int(time.time())
        
        for i, segment in enumerate(broll_segments):
            segment_id = f"segment_{i}"
            unique_key = f"broll_id_new_{segment_id}_{timestamp}_{i}"
            
            col1, col2 = st.columns([4, 1])
            with col1:
                b_roll_id = st.text_input(
                f"B-Roll ID for Segment {i+1}",
                    value=broll_ids[segment_id],
                    key=unique_key
                )
            with col2:
                if st.button(f"Reset", key=f"reset_btn_{segment_id}_{timestamp}"):
                    # This will be handled on the next rerun
                    st.session_state[unique_key] = broll_ids[segment_id]
                    st.rerun()
                    
            # Store in session state
            st.session_state.broll_fetch_ids[segment_id] = b_roll_id

# After the B-Roll ID input sections, add a Fetch Content button
st.markdown("---")
st.subheader("Fetch Existing B-Roll Content")
st.markdown("Use this button to fetch B-Roll content using the IDs provided above without generating new content.")

fetch_col1, fetch_col2 = st.columns([3, 1])

with fetch_col1:
    st.markdown("""
    This will:
    - Attempt to fetch B-Roll content using the IDs
    - Update the content status with the fetched content
    - Skip any IDs that are empty or invalid
    """)

with fetch_col2:
    if st.button("🔄 Fetch B-Roll Content", type="primary", use_container_width=True):
        with st.spinner("Fetching content from provided IDs..."):
            fetch_success = False
            
            # Count the number of IDs we have
            broll_id_count = sum(1 for id in st.session_state.broll_fetch_ids.values() if id)
            
            st.info(f"Found {broll_id_count} B-Roll IDs to fetch")
                
            # Process B-Roll IDs
            for segment_id, prompt_id in st.session_state.broll_fetch_ids.items():
                if not prompt_id:
                    continue
                
                # Set status to "fetching" to show progress
                st.session_state.content_status["broll"][segment_id] = {
                    "status": "fetching",
                    "prompt_id": prompt_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Get the appropriate API URL - assuming video API
                api_url = COMFYUI_VIDEO_API_URL
                
                # Fetch the content
                result = fetch_comfyui_content_by_id(api_url, prompt_id)
                
                if result["status"] == "success":
                    # Determine file extension based on content type
                    content_type = result.get("type", "image")
                    file_ext = "mp4" if content_type == "video" else "png"
                    
                    # Save the fetched content
                    file_path = save_media_content(
                        result["content"], 
                        "broll",
                        segment_id,
                        file_ext
                    )
                    
                    st.session_state.content_status["broll"][segment_id] = {
                        "status": "complete",
                        "file_path": file_path,
                        "prompt_id": prompt_id,
                        "content_type": content_type,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    fetch_success = True
                elif result["status"] == "processing":
                    # Content is still being generated
                    st.session_state.content_status["broll"][segment_id] = {
                        "status": "waiting",
                        "message": "ComfyUI job still processing. Try again later.",
                        "prompt_id": prompt_id,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                else:
                    # Error fetching content
                    st.session_state.content_status["broll"][segment_id] = {
                        "status": "error",
                        "message": result.get("message", "Unknown error fetching content"),
                        "prompt_id": prompt_id,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
            
            # Save the updated content status
            save_content_status()
            
            if fetch_success:
                st.success("Successfully fetched content from provided IDs!")
            else:
                st.warning("No content was fetched. Please check your IDs and try again.")
            
            st.rerun()

# Generate content section
st.markdown("---")
st.subheader("Generate Content")
st.markdown("Choose which type of content to generate:")

if st.session_state.parallel_tasks["running"]:
    progress_value = st.session_state.parallel_tasks["completed"] / max(1, st.session_state.parallel_tasks["total"])
    st.progress(progress_value)
    st.info(f"Generating content... {st.session_state.parallel_tasks['completed']} of {st.session_state.parallel_tasks['total']} tasks completed")
    
    # Refresh the page every few seconds to update progress
    st.markdown("""
    <meta http-equiv="refresh" content="3">
    """, unsafe_allow_html=True)
else:
    # Create two columns for separate generation buttons
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### A-Roll Content")
        st.markdown("Generate on-camera talking head video content")
        
        if st.button("🎬 Generate A-Roll Content", type="primary", key="generate_aroll", use_container_width=True):
            # Capture all required data before starting the thread
            temp_segments = st.session_state.segments.copy() if hasattr(st.session_state, 'segments') and st.session_state.segments else []
            temp_aroll_fetch_ids = st.session_state.aroll_fetch_ids.copy() if hasattr(st.session_state, 'aroll_fetch_ids') and st.session_state.aroll_fetch_ids else {}
            
            # Print debug info
            print(f"Debug - Starting A-Roll content generation")
            
            # Check if segments is empty
            if not temp_segments:
                st.error("No segments found. Please ensure you have completed the Script Segmentation step.")
                st.stop()
            
            # Mark as running before starting the thread
        st.session_state.parallel_tasks["running"] = True
        
        # Start the A-Roll content generation in a separate thread
        thread = threading.Thread(
            target=generate_aroll_content, 
            args=(temp_segments, temp_aroll_fetch_ids)
        )
        thread.daemon = True
        thread.start()
        
        # Refresh the page to show progress
        st.rerun()
    
    with col2:
        st.markdown("### B-Roll Content")
        st.markdown("Generate visual content based on prompts")
        
        if st.session_state.manual_upload:
            st.info("You've selected manual upload mode. Use the batch processing option or upload files manually.")
            
            if st.button("📤 Start Batch Processing", type="primary", key="batch_process", use_container_width=True):
                with st.spinner("Submitting prompts to video server..."):
                    prompt_ids, errors = batch_process_broll_prompts()
                    if prompt_ids:
                        st.success(f"Successfully submitted {len(prompt_ids)} prompts to video server!")
                    if errors:
                        st.error(f"Encountered {len(errors)} errors during submission.")
                    st.rerun()
        else:
            # Replace the original button with our new sequential implementation
            comfyui_helpers.render_broll_generation_section(unique_key="col2", project_path=project_path, save_function=save_content_status)
    
    # Still provide an option for parallel generation
    st.markdown("### Generate All B-Roll Content")
    st.info("⚠️ Note: For A-Roll (talking head) generation, please use the '5A A-Roll Video Production' page.")
    if st.button("🚀 Generate All B-Roll Content", key="parallel_generation", help="Generate B-Roll content for all segments"):
        # Capture all required data before starting the thread
        temp_segments = st.session_state.segments.copy() if hasattr(st.session_state, 'segments') and st.session_state.segments else []
        temp_broll_prompts = st.session_state.broll_prompts.copy() if hasattr(st.session_state, 'broll_prompts') and st.session_state.broll_prompts else {}
        temp_manual_upload = st.session_state.manual_upload if hasattr(st.session_state, 'manual_upload') else False
        temp_broll_fetch_ids = st.session_state.broll_fetch_ids.copy() if hasattr(st.session_state, 'broll_fetch_ids') and st.session_state.broll_fetch_ids else {}
        temp_workflow_selection = st.session_state.workflow_selection.copy() if hasattr(st.session_state, 'workflow_selection') and st.session_state.workflow_selection else {"image": "default"}
        
        # Print debug info
        print(f"Debug - Starting B-Roll content generation with {len(temp_segments)} segments")
        if len(temp_segments) > 0:
            # Log segment types
            b_roll_count = len([s for s in temp_segments if isinstance(s, dict) and s.get("type") == "B-Roll"])
            print(f"Debug - Found {b_roll_count} B-Roll segments")
        
        # Check if segments is empty
        if not temp_segments:
            st.error("No segments found. Please ensure you have completed the Script Segmentation step.")
            st.stop()
        
        # Mark as running before starting the thread
        st.session_state.parallel_tasks["running"] = True
        
        # Start the content generation in a separate thread with captured data
        thread = threading.Thread(
            target=generate_content_parallel, 
            args=(temp_segments, temp_broll_prompts, temp_manual_upload, temp_broll_fetch_ids, temp_workflow_selection)
        )
        thread.daemon = True
        thread.start()
        
        # Refresh the page to show progress
        st.rerun()

# Display generation status
if "aroll" in st.session_state.content_status and "broll" in st.session_state.content_status:
    st.markdown("---")
    st.subheader("Content Status")
    
    # Create tabs for A-Roll and B-Roll
    aroll_tab, broll_tab = st.tabs(["A-Roll Status", "B-Roll Status"])
    
    with aroll_tab:
        if st.session_state.content_status["aroll"]:
            for i, segment in enumerate(aroll_segments):
                segment_id = f"segment_{i}"
                if segment_id in st.session_state.content_status["aroll"]:
                    status = st.session_state.content_status["aroll"][segment_id]
                    
                    with st.expander(f"A-Roll Segment {i+1}", expanded=True):
                        st.markdown(f"**Segment Text:** {segment['content'][:100]}...")
                        st.markdown(f"**Status:** {status['status']}")
                        
                        if status['status'] == "complete":
                            st.markdown(f"**File:** {status['file_path']}")
                            st.markdown(f"**Generated:** {status['timestamp']}")
                        elif status['status'] == "error":
                            st.error(f"Error: {status.get('message', 'Unknown error')}")
        else:
            st.info("No A-Roll content has been generated yet.")
    
    with broll_tab:
        if st.session_state.content_status["broll"]:
            for i, segment in enumerate(broll_segments):
                segment_id = f"segment_{i}"
                if segment_id in st.session_state.content_status["broll"]:
                    status = st.session_state.content_status["broll"][segment_id]
                    
                    with st.expander(f"B-Roll Segment {i+1}", expanded=True):
                        # Display prompt info
                        if "prompts" in st.session_state.broll_prompts and segment_id in st.session_state.broll_prompts["prompts"]:
                            prompt_data = st.session_state.broll_prompts["prompts"][segment_id]
                            st.markdown(f"**Prompt:** {prompt_data.get('prompt', 'No prompt available')}")
                            st.markdown(f"**Expected Content Type:** {'Video' if prompt_data.get('is_video', False) else 'Image'}")
                        
                        # Manual upload option
                        if st.session_state.manual_upload:
                            if "prompts" in st.session_state.broll_prompts and segment_id in st.session_state.broll_prompts["prompts"]:
                                prompt_data = st.session_state.broll_prompts["prompts"][segment_id]
                                expected_type = "Video" if prompt_data.get('is_video', False) else "Image"
                            else:
                                expected_type = "Image"  # Default to image if no prompt data
                            
                            upload_col1, upload_col2 = st.columns([2, 1])
                            
                            with upload_col1:
                                # Allow either video or image files regardless of expected type
                                uploaded_file = st.file_uploader(
                                    f"Upload content for B-Roll Segment {i+1}",
                                    type=["mp4", "mov", "webm", "png", "jpg", "jpeg", "webp"],
                                    key=f"uploaded_file_{segment_id}"
                                )
                                
                                st.caption(f"Expected content type: {expected_type}, but you can upload any supported format")
                            
                            with upload_col2:
                                if uploaded_file is not None:
                                    # Determine file type from extension
                                    file_ext = uploaded_file.name.split(".")[-1].lower()
                                    is_video = file_ext in ["mp4", "mov", "webm"]
                                    
                                    # Save button
                                    if st.button(f"💾 Save to Project", key=f"save_file_{segment_id}", type="primary"):
                                        try:
                                            # Create directory if it doesn't exist
                                            media_dir = project_path / "media" / "broll"
                                            media_dir.mkdir(parents=True, exist_ok=True)
                                            
                                            # Generate filename
                                            filename = f"manual_broll_{segment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
                                            file_path = media_dir / filename
                                            
                                            # Save the file
                                            with open(file_path, "wb") as f:
                                                f.write(uploaded_file.getbuffer())
                                            
                                            # Update status
                                            st.session_state.content_status["broll"][segment_id] = {
                                                "status": "complete",
                                                "file_path": str(file_path),
                                                "type": "manual",
                                                "content_type": "video" if is_video else "image",
                                                "expected_type": "video" if prompt_data.get('is_video', False) else "image",
                                                "type_mismatch": (is_video != prompt_data.get('is_video', False)),
                                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                            }
                                            
                                            save_content_status()
                                            st.success(f"Saved file to {file_path}")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error saving file: {str(e)}")
                            
                            # Preview the file below the columns
                            if uploaded_file is not None:
                                file_ext = uploaded_file.name.split(".")[-1].lower()
                                is_video = file_ext in ["mp4", "mov", "webm"]
                                
                                st.markdown("##### Content Preview")
                                
                                # Add file info
                                uploaded_size = len(uploaded_file.getvalue()) / (1024 * 1024)  # Convert to MB
                                st.caption(f"Filename: {uploaded_file.name} ({uploaded_size:.2f} MB)")
                                
                                # Preview based on file type
                                if is_video:
                                    st.video(uploaded_file)
                                else:
                                    st.image(uploaded_file, caption=f"Uploaded image for Segment {i+1}")
                                
                                # Save to session state
                                st.session_state.uploaded_files[segment_id] = uploaded_file
                        
                        # Display status info if available
                        if segment_id in st.session_state.content_status["broll"]:
                            status = st.session_state.content_status["broll"][segment_id]
                            
                            status_text = status['status']
                            
                            # Add icon based on status
                            if status_text == "complete":
                                status_icon = "✅"
                            elif status_text == "error":
                                status_icon = "❌"
                            elif status_text == "fetching":
                                status_icon = "🔄"
                            elif status_text == "processing":
                                status_icon = "⚙️"
                            elif status_text == "waiting":
                                status_icon = "⏳"
                            else:
                                status_icon = "ℹ️"
                                
                            st.markdown(f"**Status:** {status_icon} {status_text.capitalize()}")
                            
                            # Display Prompt ID information if available
                            if 'prompt_id' in status:
                                st.markdown(f"**Prompt ID:** `{status['prompt_id']}`")
                                
                                # Add a button to retry fetching if it's in waiting status
                                if status_text == "waiting" and st.button(f"Retry Fetch for Segment {i+1}", key=f"retry_fetch_{segment_id}"):
                                    st.info("Will try fetching again on next generation run")
                                    st.rerun()
                        
                            if status_text == "complete":
                                st.markdown(f"**Generated:** {status['timestamp']}")
                                st.markdown(f"**File:** {status['file_path']}")
                                
                                # Show type mismatch warning if needed
                                if status.get('type_mismatch', False):
                                    st.warning(f"⚠️ Content type mismatch: Expected {status.get('expected_type', 'unknown')}, got {status.get('content_type', 'unknown')}")
                                
                                # If available, display a preview
                                # (For a real implementation, you'd display the actual file)
                                file_path = status['file_path']
                                if file_path.endswith(".mp4"):
                                    st.info("Video preview would appear here in the actual implementation")
                                else:
                                    st.info("Image preview would appear here in the actual implementation")
                                    
                            elif status_text == "error":
                                st.error(f"Error: {status.get('message', 'Unknown error')}")
                                
                                # Add a button to clear the error and try again
                                if st.button(f"Clear Error for Segment {i+1}", key=f"clear_error_{segment_id}"):
                                    # Remove the status entry to allow retrying
                                    if segment_id in st.session_state.content_status["broll"]:
                                        del st.session_state.content_status["broll"][segment_id]
                                    st.rerun()
                                
                            elif status_text in ["fetching", "waiting", "processing"]:
                                st.info(status.get('message', f"Content is being {status_text}..."))
                                
                                # Add a cancel button for in-progress operations
                                if st.button(f"Cancel for Segment {i+1}", key=f"cancel_{segment_id}"):
                                    # Remove the fetch ID and status to start fresh
                                    if segment_id in st.session_state.broll_fetch_ids:
                                        st.session_state.broll_fetch_ids[segment_id] = ""
                                    if segment_id in st.session_state.content_status["broll"]:
                                        del st.session_state.content_status["broll"][segment_id]
                                    st.rerun()
        else:
            st.info("No B-Roll content has been generated yet.")

# If all content is generated, show continue button
if (not st.session_state.parallel_tasks["running"] and 
    st.session_state.content_status["aroll"] and 
    st.session_state.content_status["broll"]):
    
    # Check if all segments have content generated
    aroll_complete = all(status.get("status") == "complete" 
                        for status in st.session_state.content_status["aroll"].values())
    
    broll_segments_with_prompts = [f"segment_{i}" for i, _ in enumerate(broll_segments)]
    broll_complete = all(status.get("status") == "complete"
                        for segment_id, status in st.session_state.content_status["broll"].items()
                        if segment_id in broll_segments_with_prompts)
    
    if aroll_complete and broll_complete:
        st.success("All content has been successfully generated! You can now proceed to video assembly.")
        mark_step_complete("step_5")
    else:
        # Show which segments need attention
        segments_with_issues = []
        
        for i, segment in enumerate(aroll_segments):
            segment_id = f"segment_{i}"
            if segment_id in st.session_state.content_status["aroll"]:
                status = st.session_state.content_status["aroll"][segment_id]
                if status.get("status") != "complete":
                    segments_with_issues.append(f"A-Roll Segment {i+1}")
        
        for i, segment in enumerate(broll_segments):
            segment_id = f"segment_{i}"
            if segment_id in st.session_state.content_status["broll"]:
                status = st.session_state.content_status["broll"][segment_id]
                if status.get("status") != "complete":
                    segments_with_issues.append(f"B-Roll Segment {i+1}")
        
        st.warning(f"Some segments need attention: {', '.join(segments_with_issues)}")

# Navigation buttons
st.markdown("---")
render_step_navigation(
    current_step=5,
    prev_step_path="pages/5A_ARoll_Video_Production.py",
    next_step_path="pages/6_Video_Assembly.py"
)

# Debug section (hidden by default)
with st.expander("Debug Information", expanded=False):
    st.markdown("### Session State Debug")
    
    st.markdown("#### Segments Information")
    segments = st.session_state.segments if hasattr(st.session_state, 'segments') else []
    st.write(f"Total segments: {len(segments)}")
    
    # Count segment types
    a_roll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
    b_roll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll"]
    invalid_segments = [s for s in segments if not isinstance(s, dict) or "type" not in s or s.get("type") not in ["A-Roll", "B-Roll"]]
    
    st.write(f"A-Roll segments: {len(a_roll_segments)}")
    st.write(f"B-Roll segments: {len(b_roll_segments)}")
    st.write(f"Invalid segments: {len(invalid_segments)}")
    
    if st.button("Show Full Segments Data"):
        st.json(segments)
    
    st.markdown("#### B-Roll Prompts Information")
    prompts = st.session_state.broll_prompts if hasattr(st.session_state, 'broll_prompts') else {}
    st.write(f"B-Roll prompts object type: {type(prompts).__name__}")
    
    if isinstance(prompts, dict):
        if "prompts" in prompts:
            prompt_count = len(prompts.get("prompts", {}))
            st.write(f"Number of individual prompts: {prompt_count}")
        else:
            st.write("No 'prompts' key found in broll_prompts")
    
    if st.button("Show Full B-Roll Prompts Data"):
        st.json(prompts)
    
    st.markdown("#### Project Path")
    st.write(f"Project path: {project_path}")
    
    # Button to check if files exist
    if st.button("Check Project Files"):
        script_file = project_path / "script.json"
        prompts_file = project_path / "broll_prompts.json"
        
        st.write(f"script.json exists: {script_file.exists()}")
        st.write(f"broll_prompts.json exists: {prompts_file.exists()}")
        
        if script_file.exists():
            try:
                with open(script_file, "r") as f:
                    script_data = json.load(f)
                    st.write(f"script.json is valid JSON: True")
                    st.write(f"script.json has 'segments' key: {'segments' in script_data}")
                    if 'segments' in script_data:
                        st.write(f"Number of segments in file: {len(script_data['segments'])}")
            except json.JSONDecodeError:
                st.write(f"script.json is valid JSON: False")
            except Exception as e:
                st.write(f"Error reading script.json: {str(e)}")
        
        if prompts_file.exists():
            try:
                with open(prompts_file, "r") as f:
                    prompts_data = json.load(f)
                    st.write(f"broll_prompts.json is valid JSON: True")
                    st.write(f"broll_prompts.json has 'prompts' key: {'prompts' in prompts_data}")
                    if 'prompts' in prompts_data:
                        st.write(f"Number of prompts in file: {len(prompts_data['prompts'])}")
            except json.JSONDecodeError:
                st.write(f"broll_prompts.json is valid JSON: False")
            except Exception as e:
                st.write(f"Error reading broll_prompts.json: {str(e)}")
    
    # Refresh button
    if st.button("Reload Page Data"):
        _ = load_script_data()
        _ = load_broll_prompts()
        _ = load_content_status()
        st.rerun() 

# Add this function to allow clearing cached IDs
def clear_fetch_ids():
    """Clear cached IDs for A-Roll and B-Roll content"""
    if "aroll_fetch_ids" in st.session_state:
        st.session_state.aroll_fetch_ids = {}
    if "broll_fetch_ids" in st.session_state:
        st.session_state.broll_fetch_ids = {}
    st.success("✅ Content cache cleared successfully. New content will be generated on the next run.")
    
    # Also clear any active tracking
    if "active_trackers" in st.session_state:
        st.session_state.active_trackers = []

# Add a new UI section for cache management
with st.expander("🧹 Cache Management"):
    st.markdown("""
    ### Clear Content Cache
    
    If you're experiencing issues with content generation, or if you want to force regeneration of all content,
    you can clear the cached content IDs here.
    
    **Note:** This won't delete any previously generated files, but will ensure new content is generated
    the next time you run the generation process.
    """)
    
    if st.button("🗑️ Clear Content Cache", key="clear_cache"):
        clear_fetch_ids()

# Load workflow files
def load_workflow(workflow_type="video"):
    """Load workflow from JSON file"""
    try:
        if workflow_type == "video":
            workflow_file = "wan.json"
        else:
            workflow_file = "image_homepc.json"
            
        with open(workflow_file, "r") as f:
            workflow = json.load(f)
            print(f"✅ Loaded {workflow_type} workflow from {workflow_file} with {len(workflow)} nodes")
            return workflow
    except Exception as e:
        st.error(f"Failed to load workflow file: {str(e)}")
        return None

# Function to modify workflow with custom parameters
def modify_workflow(workflow, params):
    """Modify the loaded workflow JSON with custom parameters"""
    try:
        if workflow is None:
            return None
            
        # Create a deep copy to avoid modifying the original
        modified_workflow = workflow.copy()
        
        # Find text input nodes (for prompt) - search for nodes with CLIPTextEncode class_type
        text_nodes = [k for k in modified_workflow.keys() 
                     if "class_type" in modified_workflow[k] and 
                     modified_workflow[k]["class_type"] == "CLIPTextEncode"]
        
        # Find negative text nodes - typically the second CLIPTextEncode node
        if len(text_nodes) >= 2:
            # First node for positive prompt, second for negative
            pos_node_id = text_nodes[0]
            neg_node_id = text_nodes[1]
            
            # Set prompts
            if "inputs" in modified_workflow[pos_node_id]:
                modified_workflow[pos_node_id]["inputs"]["text"] = params.get("prompt", "")
                print(f"Set prompt in node {pos_node_id}")
                
            if "inputs" in modified_workflow[neg_node_id]:
                modified_workflow[neg_node_id]["inputs"]["text"] = params.get("negative_prompt", "")
                print(f"Set negative prompt in node {neg_node_id}")
        
        # Find empty latent image nodes for dimensions
        latent_nodes = [k for k in modified_workflow.keys() 
                       if "class_type" in modified_workflow[k] and 
                       (modified_workflow[k]["class_type"] == "EmptyLatentImage" or
                        modified_workflow[k]["class_type"] == "EmptyLatentVideo")]
        
        if latent_nodes:
            latent_node_id = latent_nodes[0]
            if "inputs" in modified_workflow[latent_node_id]:
                if "width" in modified_workflow[latent_node_id]["inputs"]:
                    modified_workflow[latent_node_id]["inputs"]["width"] = params.get("width", 1080)
                if "height" in modified_workflow[latent_node_id]["inputs"]:
                    modified_workflow[latent_node_id]["inputs"]["height"] = params.get("height", 1920)
                print(f"Set dimensions in node {latent_node_id}")
        
        # Find sampler nodes for seed
        sampler_nodes = [k for k in modified_workflow.keys() 
                        if "class_type" in modified_workflow[k] and 
                        ("KSampler" in modified_workflow[k]["class_type"] or 
                         "SamplerAdvanced" in modified_workflow[k]["class_type"])]
        
        if sampler_nodes:
            sampler_node_id = sampler_nodes[0]
            if "inputs" in modified_workflow[sampler_node_id] and "seed" in modified_workflow[sampler_node_id]["inputs"]:
                modified_workflow[sampler_node_id]["inputs"]["seed"] = params.get("seed", random.randint(1, 999999999))
                print(f"Set seed in node {sampler_node_id}")
        
        return modified_workflow
        
    except Exception as e:
        print(f"Error modifying workflow: {str(e)}")
        return None

# Function to fetch content by prompt ID
def fetch_content_by_id(prompt_id, api_url):
    """Fetch content from ComfyUI using prompt ID"""
    try:
        # First check history
        history_url = f"{api_url}/history/{prompt_id}"
        history_response = requests.get(history_url, timeout=10)
        
        if history_response.status_code != 200:
            return {
                "status": "error",
                "message": f"Error fetching history: {history_response.status_code}"
            }
        
        job_data = history_response.json()
        
        # Check if job exists
        if prompt_id not in job_data:
            return {
                "status": "error",
                "message": "Prompt ID not found in history"
            }
        
        # Get job info
        job_info = job_data[prompt_id]
        
        # Check if job completed
        outputs = job_info.get("outputs", {})
        if not outputs:
            return {
                "status": "processing",
                "message": "Job still processing"
            }
        
        # Find output file
        for node_id, node_data in outputs.items():
            # Check for images
            if "images" in node_data:
                for image_data in node_data["images"]:
                    filename = image_data.get("filename", "")
                    
                    if filename:
                        # Download file
                        file_url = f"{api_url}/view?filename={filename}"
                        content_response = requests.get(file_url, timeout=30)
                        
                        if content_response.status_code == 200:
                            return {
                                "status": "success",
                                "content": content_response.content,
                                "filename": filename,
                                "type": "image"
                            }
            
            # Check for videos
            for media_type in ["videos", "gifs"]:
                if media_type in node_data:
                    for media_item in node_data[media_type]:
                        filename = media_item.get("filename", "")
                        
                        if filename:
                            # Download file
                            file_url = f"{api_url}/view?filename={filename}"
                            content_response = requests.get(file_url, timeout=60)
                            
                            if content_response.status_code == 200:
                                return {
                                    "status": "success",
                                    "content": content_response.content,
                                    "filename": filename,
                                    "type": "video"
                                }
        
        # If we get here, try looking for AnimateDiff pattern files
        possible_files = [f"animation_{i:05d}.mp4" for i in range(1, 10)]
        for filename in possible_files:
            file_url = f"{api_url}/view?filename={filename}"
            try:
                response = requests.head(file_url, timeout=5)
                if response.status_code == 200:
                    content_response = requests.get(file_url, timeout=60)
                    if content_response.status_code == 200:
                        return {
                            "status": "success",
                            "content": content_response.content,
                            "filename": filename,
                            "type": "video"
                        }
            except Exception as e:
                print(f"Error checking alternative file {filename}: {str(e)}")
        
        return {
            "status": "error",
            "message": "No output file found"
        }
    
    except Exception as e:
        st.error(f"Error fetching content: {str(e)}")
        return {
            "status": "error",
            "message": f"Error fetching content: {str(e)}"
        }

# Function to periodically fetch content until it's available
def periodic_content_fetch(prompt_id, api_url, max_attempts=30, interval=3):
    """Periodically fetch content by prompt ID until it's available or max attempts reached"""
    status_placeholder = st.empty()
    status_placeholder.info(f"⏳ Waiting for content generation to complete (ID: {prompt_id})...")
    
    for attempt in range(1, max_attempts + 1):
        status_placeholder.text(f"Fetch attempt {attempt}/{max_attempts}...")
        
        # Try to fetch content
        result = fetch_content_by_id(prompt_id, api_url)
        
        if result["status"] == "success":
            status_placeholder.success("✅ Content successfully generated!")
            return result
        elif result["status"] == "error" and "not found" in result.get("message", "").lower():
            # If prompt ID is not found, stop trying
            status_placeholder.error("❌ Prompt ID not found")
            return result
        
        # Wait before trying again
        time.sleep(interval)
    
    # If we reached max attempts
    status_placeholder.error("❌ Timed out waiting for content")
    return {
        "status": "error",
        "message": f"Timed out after {max_attempts} attempts"
    }

# Function to save media content to file
def save_media_content(content, segment_type, segment_id, file_extension):
    """Save media content to a file"""
    # Create directories if they don't exist
    media_dir = project_path / "media" / segment_type
    media_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{segment_type}_{segment_id}_{timestamp}.{file_extension}"
    
    # Save file
    file_path = media_dir / filename
    with open(file_path, "wb") as f:
        f.write(content)
    
    # Return relative path from project directory
    return str(file_path)

# Function to generate B-Roll sequentially
def generate_broll_sequentially(segments_data, api_url=None):
    """Generate B-Roll content sequentially with proper tracking"""
    if api_url is None:
        api_url = "http://100.115.243.42:8000"
    
    # Track progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Store results
    results = {}
    total_segments = len(segments_data)
    
    # Process each segment
    for idx, (segment_id, segment_data) in enumerate(segments_data.items()):
        # Update progress
        progress_value = idx / total_segments
        progress_bar.progress(progress_value)
        status_text.text(f"Processing segment {idx+1}/{total_segments}: {segment_id}")
        
        # Create segment container for output
        segment_container = st.container()
        
        with segment_container:
            st.subheader(f"Segment {segment_id}")
            
            # Check if is_video flag exists, default to True for B-Roll
            is_video = segment_data.get("is_video", True)
            content_type = "video" if is_video else "image"
            
            # Create client ID for tracking
            client_id = f"streamlit_broll_{segment_id}_{int(time.time())}"
            
            # Load workflow
            workflow = load_workflow("video" if is_video else "image")
            if workflow is None:
                st.error(f"Failed to load workflow for {segment_id}")
                results[segment_id] = {"status": "error", "message": "Failed to load workflow"}
                continue
                
            # Get parameters
            params = {
                "prompt": segment_data.get("prompt", ""),
                "negative_prompt": segment_data.get("negative_prompt", "ugly, blurry, low quality, deformed"),
                "width": 1080,
                "height": 1920,
                "seed": random.randint(1, 999999999)
            }
            
            # Modify workflow
            modified_workflow = modify_workflow(workflow, params)
            if modified_workflow is None:
                st.error(f"Failed to modify workflow for {segment_id}")
                results[segment_id] = {"status": "error", "message": "Failed to modify workflow"}
                continue
            
            # Submit job
            st.info(f"Submitting {content_type} generation job")
            result = comfyui_api.queue_prompt(modified_workflow, client_id, api_url)
            
            # Check result
            if result["status_code"] != 200 or not result.get("prompt_id"):
                st.error(f"Failed to submit job: {result.get('error', 'Unknown error')}")
                results[segment_id] = {"status": "error", "message": f"Job submission failed: {result.get('error', 'Unknown error')}"}
                continue
                
            prompt_id = result["prompt_id"]
            st.info(f"Job submitted with ID: {prompt_id}")
            
            # Store the prompt ID
            if "broll_fetch_ids" not in st.session_state:
                st.session_state.broll_fetch_ids = {}
            st.session_state.broll_fetch_ids[segment_id] = prompt_id
            
            # Fetch content
            st.info("Waiting for content generation to complete...")
            fetch_result = periodic_content_fetch(prompt_id, api_url)
            
            if fetch_result["status"] == "success":
                # Save content
                content = fetch_result["content"]
                file_ext = "mp4" if is_video else "png"
                file_path = save_media_content(content, "broll", segment_id, file_ext)
                
                # Update status
                st.session_state.content_status["broll"][segment_id] = {
                    "status": "complete",
                    "file_path": file_path,
                    "prompt_id": prompt_id,
                    "content_type": content_type,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                
                # Display result
                st.success(f"Successfully generated {content_type} for segment {segment_id}")
                if is_video:
                    st.video(file_path)
                else:
                    st.image(file_path)
                    
                results[segment_id] = {
                    "status": "success", 
                    "file_path": file_path,
                    "prompt_id": prompt_id
                }
            else:
                # Try direct download for AnimateDiff patterns
                if is_video:
                    downloaded = False
                    possible_files = [f"animation_{i:05d}.mp4" for i in range(1, 10)]
                    
                    for filename in possible_files:
                        file_url = f"{api_url}/view?filename={filename}"
                        try:
                            response = requests.head(file_url, timeout=5)
                            if response.status_code == 200:
                                content_response = requests.get(file_url, timeout=60)
                                if content_response.status_code == 200:
                                    # Save file
                                    file_path = save_media_content(content_response.content, "broll", segment_id, "mp4")
                                    
                                    # Update status
                                    st.session_state.content_status["broll"][segment_id] = {
                                        "status": "complete",
                                        "file_path": file_path,
                                        "prompt_id": prompt_id,
                                        "content_type": "video",
                                        "filename": filename,
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                    }
                                    
                                    st.success(f"Found and downloaded video from pattern {filename}")
                                    st.video(file_path)
                                    
                                    results[segment_id] = {
                                        "status": "success", 
                                        "file_path": file_path,
                                        "prompt_id": prompt_id
                                    }
                                    downloaded = True
                                    break
                        except Exception as e:
                            st.warning(f"Error checking file {filename}: {str(e)}")
                
                    if not downloaded:
                        st.error(f"Failed to generate content: {fetch_result.get('message', 'Unknown error')}")
                        results[segment_id] = {"status": "error", "message": fetch_result.get('message', 'Content generation failed')}
                else:
                    st.error(f"Failed to generate content: {fetch_result.get('message', 'Unknown error')}")
                    results[segment_id] = {"status": "error", "message": fetch_result.get('message', 'Content generation failed')}
            
            # Add a separator between segments
            st.divider()
            
            # Wait a bit before next job to give ComfyUI time to recover
            if idx < total_segments - 1:
                time.sleep(3)
    
    # Update final progress
    progress_bar.progress(1.0)
    status_text.text(f"Completed processing {total_segments} segments!")
    
    return results

# Define the B-Roll generation UI function
def render_broll_generation_section(unique_key="main"):
    """Render the B-Roll generation section with a single 'Generate All B-Roll' button
    
    Args:
        unique_key: A unique identifier to append to widget keys to avoid duplicates
    """
    # Create a single column for B-roll generation (removing the two-column approach)
    broll_gen_col = st.container()
    
    with broll_gen_col:
        if st.button("🎨 Generate All B-Roll", type="primary", key=f"generate_broll_{unique_key}", use_container_width=True):
            # Capture all required data before starting the thread
            temp_segments = st.session_state.segments.copy() if hasattr(st.session_state, 'segments') and st.session_state.segments else []
            temp_broll_prompts = st.session_state.broll_prompts.copy() if hasattr(st.session_state, 'broll_prompts') else {'prompts': {}}
            
            # Check if we have B-roll segments to process
            broll_segments = {}
            for i, seg in enumerate(temp_segments):
                segment_id = f"segment_{i}"
                if segment_id in temp_broll_prompts.get('prompts', {}):
                    broll_segments[segment_id] = temp_broll_prompts['prompts'][segment_id]
            
            if not broll_segments:
                st.error("No B-roll segments to process. Please create segments first.")
            else:
                # Generate B-roll sequentially
                st.subheader("B-Roll Generation in Progress")
                result = generate_broll_sequentially(broll_segments)
                
                # Save updated content status
                save_content_status()
                
                # Show summary
                success_count = sum(1 for r in result.values() if r.get('status') == 'success')
                st.success(f"Completed B-roll generation: {success_count} successful out of {len(broll_segments)} segments.")
                
                # Mark step as complete if all segments succeeded
                if success_count == len(broll_segments):
                    mark_step_complete('content_production')
                    st.balloons()  # Add some fun!