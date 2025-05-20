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

# Add the app directory to Python path for relative imports
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from components.navigation import render_workflow_navigation, render_step_navigation
from components.progress import render_step_header
from utils.session_state import get_settings, get_project_path, mark_step_complete
from utils.progress_tracker import start_comfyui_tracking

# Set page configuration
st.set_page_config(
    page_title="Content Production | AI Money Printer",
    page_icon="⚡",
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
        "aroll": {},
        "broll": {}
    }
if "parallel_tasks" not in st.session_state:
    st.session_state.parallel_tasks = {
        "running": False,
        "completed": 0,
        "total": 0
    }
if "aroll_fetch_ids" not in st.session_state:
    # Initialize with default A-Roll IDs
    st.session_state.aroll_fetch_ids = {
        "segment_0": "5169ef5a328149a8b13c365ee7060106",  # SEG1
        "segment_2": "aed87db0234e4965825c7ee4c1067467",  # SEG3
        "segment_4": "e7d47355c21e4190bad8752c799343ee",  # SEG5
        "segment_6": "36064085e2a240768a8368bc6a911aea"   # SEG7
    }
if "broll_fetch_ids" not in st.session_state:
    # Initialize with default B-Roll IDs
    st.session_state.broll_fetch_ids = {
        "segment_0": "9a148fa4-66a8-4e43-83c4-7c553a53a9a0",  # SEG1
        "segment_1": "c7f3960f-d3f3-4095-b7fa-66f9a6087cef",  # SEG2
        "segment_2": "d2526241-6f3e-4a6e-a193-c3bd7870b6db"   # SEG3
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

# Function to load saved script and segments
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
                aroll_count = sum(1 for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll")
                broll_count = sum(1 for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll")
                invalid_count = len(segments) - aroll_count - broll_count
                
                print(f"Debug - Found {aroll_count} A-Roll, {broll_count} B-Roll, and {invalid_count} invalid segments")
                
                # Only update if we have valid segments
                if aroll_count > 0 or broll_count > 0:
                    st.session_state.segments = segments
                    return True
                else:
                    print("Warning: No valid A-Roll or B-Roll segments found in script.json")
                    return False
        except json.JSONDecodeError:
            print(f"Error: script.json is not valid JSON")
            return False
        except Exception as e:
            print(f"Error loading script data: {str(e)}")
            return False
    else:
        print(f"Script file not found at: {script_file}")
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
                    print(f"Warning: B-Roll prompts file does not contain a dictionary")
                    return False
                    
                if "prompts" not in data:
                    print(f"Warning: B-Roll prompts file does not contain a 'prompts' key")
                    return False
                    
                prompts = data.get("prompts", {})
                if not prompts or not isinstance(prompts, dict):
                    print(f"Warning: B-Roll prompts are empty or not a dictionary: {prompts}")
                    return False
                
                # Count the number of prompts
                prompt_count = len(prompts)
                print(f"Debug - Found {prompt_count} B-Roll prompts")
                
                # Update session state if we have valid prompts
                if prompt_count > 0:
                    st.session_state.broll_prompts = data
                    return True
                else:
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
        with open(status_file, "r") as f:
            st.session_state.content_status = json.load(f)
            return True
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
    try:
        # Submit the workflow to /prompt endpoint
        response = requests.post(
            f"{api_url}/prompt",
            json={"prompt": workflow}
        )
        
        if response.status_code == 200:
            data = response.json()
            return data.get("prompt_id")
        else:
            st.error(f"Error submitting job: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error connecting to ComfyUI: {str(e)}")
        return None

# Function to check ComfyUI job status
def check_comfyui_job_status(api_url, prompt_id):
    try:
        response = requests.get(f"{api_url}/history/{prompt_id}")
        if response.status_code == 200:
            data = response.json()
            if prompt_id in data:
                job_data = data[prompt_id]
                
                # Check for status information in new format
                if "status" in job_data and isinstance(job_data["status"], dict):
                    # Look for status_str field (newer ComfyUI API format)
                    if "status_str" in job_data["status"]:
                        status_str = job_data["status"]["status_str"]
                        
                        if status_str == "success":
                            return {"status": "complete", "data": job_data.get("outputs", {})}
                        elif status_str == "error":
                            error_msg = "Unknown error"
                            # Try to extract error message from messages
                            if "messages" in job_data["status"]:
                                for msg in job_data["status"]["messages"]:
                                    if len(msg) >= 2 and msg[0] == "execution_error" and isinstance(msg[1], dict):
                                        error_msg = msg[1].get("exception_message", error_msg)
                                        break
                            return {"status": "error", "message": error_msg}
                        elif status_str == "processing":
                            return {"status": "processing"}
                        else:
                            return {"status": status_str}
                    
                    # Look for completed flag
                    if "completed" in job_data["status"]:
                        if job_data["status"]["completed"] == True:
                            return {"status": "complete", "data": job_data.get("outputs", {})}
                    
                    # Look for messages indicating success or error
                    if "messages" in job_data["status"]:
                        for message in job_data["status"]["messages"]:
                            if len(message) >= 2:
                                if message[0] == "execution_success":
                                    return {"status": "complete", "data": job_data.get("outputs", {})}
                                elif message[0] == "execution_error":
                                    error_msg = "Unknown error"
                                    if isinstance(message[1], dict):
                                        error_msg = message[1].get("exception_message", error_msg)
                                    return {"status": "error", "message": error_msg}
                
                # Fallback: Check if there are outputs
                if "outputs" in job_data and job_data["outputs"]:
                    return {"status": "complete", "data": job_data["outputs"]}
                    
                # Default to processing if we're unsure
                return {"status": "processing"}
            else:
                return {"status": "not_found"}
        else:
            return {"status": "error", "message": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
def fetch_comfyui_content_by_id(api_url, prompt_id):
    try:
        # First check if the job exists in history
        history_response = requests.get(f"{api_url}/history/{prompt_id}", timeout=10)
        
        if history_response.status_code != 200:
            return {"status": "error", "message": f"Error fetching history: {history_response.status_code}"}
            
        job_data = history_response.json()
        
        # Check if job data exists
        if prompt_id not in job_data:
            return {"status": "error", "message": "Prompt ID not found in history"}
            
        # Get the job data
        job_info = job_data[prompt_id]
        
        # Determine job status
        job_status = "unknown"
        if "status" in job_info and isinstance(job_info["status"], dict):
            if "status_str" in job_info["status"]:
                job_status = job_info["status"]["status_str"]
            elif "completed" in job_info["status"] and job_info["status"]["completed"] == True:
                job_status = "success"
            elif "messages" in job_info["status"]:
                for message in job_info["status"]["messages"]:
                    if len(message) >= 2:
                        if message[0] == "execution_success":
                            job_status = "success"
                            break
                        elif message[0] == "execution_error":
                            job_status = "error"
                            break
        
        # Check if job completed successfully based on status or outputs
        if job_status == "success" or ("outputs" in job_info and job_info["outputs"]):
            outputs = job_info.get("outputs", {})
            
            # Extract the filename from the outputs
            # Iterate through output nodes to find image/video output
            for node_id, node_data in outputs.items():
                if "images" in node_data:
                    # Found images output
                    for image_data in node_data["images"]:
                        filename = image_data["filename"]
                        file_type = image_data.get("type", "image")
                        
                        # Download the file directly using the /view endpoint
                        file_url = f"{api_url}/view?filename={filename}"
                        content_response = requests.get(file_url, timeout=30)
                        
                        if content_response.status_code == 200:
                            return {
                                "status": "success",
                                "content": content_response.content,
                                "filename": filename,
                                "prompt_id": prompt_id,
                                "type": file_type
                            }
                # Check for video output (might have different structure)
                elif "gifs" in node_data or "videos" in node_data:
                    # Handle video outputs (usually in videos array)
                    video_list = node_data.get("videos", node_data.get("gifs", []))
                    if video_list:
                        for video_data in video_list:
                            filename = video_data.get("filename", "")
                            if filename:
                                # Download the video file
                                file_url = f"{api_url}/view?filename={filename}"
                                content_response = requests.get(file_url, timeout=60)  # Longer timeout for videos
                                
                                if content_response.status_code == 200:
                                    return {
                                        "status": "success",
                                        "content": content_response.content,
                                        "filename": filename,
                                        "prompt_id": prompt_id,
                                        "type": "video"
                                    }
            
            # If we got here, we couldn't find any output files
            return {"status": "error", "message": "No output file found in job results"}
        elif job_status == "error":
            # Job failed
            error_message = "Unknown error"
            if "status" in job_info and "messages" in job_info["status"]:
                for msg in job_info["status"]["messages"]:
                    if len(msg) >= 2 and msg[0] == "execution_error" and isinstance(msg[1], dict):
                        error_message = msg[1].get("exception_message", error_message)
                        break
            return {"status": "error", "message": f"Job failed: {error_message}"}
        else:
            # Job is still processing
            return {"status": "processing", "message": "Job is still processing"}
            
    except requests.exceptions.Timeout:
        return {"status": "error", "message": "Timeout while fetching content"}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": f"Could not connect to ComfyUI API at {api_url}"}
    except Exception as e:
        return {"status": "error", "message": f"Error fetching content: {str(e)}"}

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
    
    return prompt_ids, errors

# Function for parallel content generation
def generate_content_parallel(segments, broll_prompts, manual_upload, aroll_fetch_ids, broll_fetch_ids, workflow_selection):
    # Ensure parallel_tasks is properly initialized first
    if "parallel_tasks" not in st.session_state:
        st.session_state.parallel_tasks = {
            "running": True,
            "completed": 0,
            "total": 0
        }
    
    # Reset progress tracking
    st.session_state.parallel_tasks["completed"] = 0
    
    # Get all segments that need to be processed
    aroll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "A-Roll"]
    broll_segments = [s for s in segments if isinstance(s, dict) and s.get("type") == "B-Roll"]
    
    # Debug log for segments
    print(f"Found {len(aroll_segments)} A-Roll and {len(broll_segments)} B-Roll segments")
    
    # Set minimum total tasks to 1 to avoid division by zero
    if manual_upload:
        total_tasks = len(aroll_segments)
    else:
        total_tasks = len(aroll_segments) + len(broll_segments)
    
    # Ensure we have at least 1 task to avoid division by zero in progress calculations
    st.session_state.parallel_tasks["total"] = max(1, total_tasks)
    
    if total_tasks == 0:
        print("Warning: No segments found for processing")
        # Mark as complete immediately if no segments to process
        st.session_state.parallel_tasks["completed"] = 1
        st.session_state.parallel_tasks["running"] = False
        return
    
    # Store trackers to keep references (prevent garbage collection)
    if "active_trackers" not in st.session_state:
        st.session_state.active_trackers = []
    
    # Process A-Roll segments first (usually faster)
    for i, segment in enumerate(aroll_segments):
        segment_id = f"segment_{i}"
        
        # Check if we're using an existing A-Roll via ID
        if segment_id in aroll_fetch_ids and aroll_fetch_ids[segment_id]:
            # Logic for fetching existing A-Roll content would go here
            # For now, we'll just mark it as completed
            st.session_state.content_status["aroll"][segment_id] = {
                "status": "complete",
                "file_path": f"Fetched via ID: {aroll_fetch_ids[segment_id]}",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            # For now, we'll simulate A-Roll generation (would be replaced with actual API calls)
            time.sleep(2)  # Simulate processing time
            st.session_state.content_status["aroll"][segment_id] = {
                "status": "complete",
                "file_path": f"simulated_aroll_{segment_id}.mp4",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        # Update progress
        st.session_state.parallel_tasks["completed"] += 1
    
    # Process B-Roll segments only if not in manual upload mode
    if not manual_upload:
        # Get workflow template based on selection
        image_workflow_type = workflow_selection["image"]
        image_template_file = JSON_TEMPLATES["image"][image_workflow_type]
        
        for i, segment in enumerate(broll_segments):
            segment_id = f"segment_{i}"
            
            # Check if we have prompts for this segment
            if "prompts" in broll_prompts and segment_id in broll_prompts["prompts"]:
                prompt_data = broll_prompts["prompts"][segment_id]
                
                # Check if we're using an existing B-Roll via ID
                if segment_id in broll_fetch_ids and broll_fetch_ids[segment_id]:
                    # Set status to "fetching" to show progress
                    st.session_state.content_status["broll"][segment_id] = {
                        "status": "fetching",
                        "prompt_id": broll_fetch_ids[segment_id],
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                    # Select the correct API endpoint based on content type
                    api_url = COMFYUI_VIDEO_API_URL if prompt_data.get("is_video", False) else COMFYUI_IMAGE_API_URL
                    
                    # Setup progress tracking for this fetch
                    prompt_id = broll_fetch_ids[segment_id]
                    tracker = start_comfyui_tracking(prompt_id, api_url)
                    st.session_state.active_trackers.append(tracker)
                    
                    # Fetch existing content by ID
                    result = fetch_comfyui_content_by_id(api_url, broll_fetch_ids[segment_id])
                    
                    # Handle different result statuses
                    if result["status"] == "success":
                        # Determine file extension based on content type
                        content_type = result.get("type", "image")
                        file_ext = "mp4" if content_type == "video" else "png"
                        
                        # If content type doesn't match what we expected, log a warning
                        if (content_type == "video" and not prompt_data.get("is_video", False)) or \
                           (content_type == "image" and prompt_data.get("is_video", True)):
                            mismatched_type = True
                        else:
                            mismatched_type = False
                        
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
                            "prompt_id": broll_fetch_ids[segment_id],
                            "content_type": content_type,
                            "expected_type": "video" if prompt_data.get("is_video", False) else "image",
                            "type_mismatch": mismatched_type,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    elif result["status"] == "processing":
                        # Content is still being generated
                        st.session_state.content_status["broll"][segment_id] = {
                            "status": "waiting",
                            "message": "ComfyUI job still processing. Try again later.",
                            "prompt_id": broll_fetch_ids[segment_id],
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    else:
                        # Error fetching content
                        st.session_state.content_status["broll"][segment_id] = {
                            "status": "error",
                            "message": result.get("message", "Unknown error fetching content"),
                            "prompt_id": broll_fetch_ids[segment_id],
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                else:
                    # Generate new B-Roll content
                    # Prepare the workflow with the correct template based on content type
                    template_file = JSON_TEMPLATES["video"] if prompt_data.get("is_video", False) else image_template_file
                    workflow = prepare_comfyui_workflow(
                        template_file,
                        prompt_data["prompt"],
                        prompt_data.get("negative_prompt", "ugly, blurry, low quality"),
                        resolution="1080x1920"
                    )
                    
                    if workflow:
                        # Set status to processing
                        st.session_state.content_status["broll"][segment_id] = {
                            "status": "processing",
                            "message": "Submitting job to ComfyUI...",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                        
                        # Select API based on content type
                        api_url = COMFYUI_VIDEO_API_URL if prompt_data.get("is_video", False) else COMFYUI_IMAGE_API_URL
                        
                        # Submit to ComfyUI
                        prompt_id = submit_comfyui_job(api_url, workflow)
                        
                        if prompt_id:
                            # Save the prompt ID for future use
                            broll_fetch_ids[segment_id] = prompt_id
                            
                            # Also update the session state version
                            if "broll_fetch_ids" in st.session_state:
                                st.session_state.broll_fetch_ids[segment_id] = prompt_id
                            
                            # Setup progress tracking
                            tracker = start_comfyui_tracking(prompt_id, api_url)
                            st.session_state.active_trackers.append(tracker)
                            
                            # Update status
                            st.session_state.content_status["broll"][segment_id] = {
                                "status": "processing",
                                "message": "Job submitted, processing in ComfyUI...",
                                "prompt_id": prompt_id,
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                        else:
                            # Failed to submit job
                            st.session_state.content_status["broll"][segment_id] = {
                                "status": "error",
                                "message": "Failed to submit job to ComfyUI",
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            }
                    else:
                        # Failed to prepare workflow
                        st.session_state.content_status["broll"][segment_id] = {
                            "status": "error",
                            "message": "Failed to prepare workflow",
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
            else:
                st.session_state.content_status["broll"][segment_id] = {
                    "status": "error",
                    "message": "No prompt data found for this segment",
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            
            # Update progress
            st.session_state.parallel_tasks["completed"] += 1
    
    # Save content status to file
    save_content_status()
    
    # Update session state with any changes to broll_fetch_ids
    if "broll_fetch_ids" in st.session_state:
        for segment_id, prompt_id in broll_fetch_ids.items():
            st.session_state.broll_fetch_ids[segment_id] = prompt_id
    
    # Mark generation as complete
    st.session_state.parallel_tasks["running"] = False

# Page header
render_step_header(5, "Content Production", 8)
st.title("⚡ Parallel Content Production")
st.markdown("""
Generate both A-Roll (on-camera) and B-Roll (visual) content in parallel to maximize efficiency.
This step will use the prompts generated in the previous step to create all the visual assets for your video.
""")

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
        st.caption("Optional: Enter prompt IDs to use existing B-Roll content")
        
        for i, segment in enumerate(broll_segments):
            segment_id = f"segment_{i}"
            fetch_id = st.text_input(
                f"B-Roll ID for Segment {i+1}",
                value=st.session_state.broll_fetch_ids.get(segment_id, ""),
                key=f"broll_id_{segment_id}"
            )
            st.session_state.broll_fetch_ids[segment_id] = fetch_id

# After the B-Roll ID input sections, add a Fetch Content button
st.markdown("---")
st.subheader("Fetch Existing Content")
st.markdown("Use this button to fetch content using the IDs provided above without generating new content.")

fetch_col1, fetch_col2 = st.columns([3, 1])

with fetch_col1:
    st.markdown("""
    This will:
    - Attempt to fetch all A-Roll and B-Roll content using the IDs
    - Update the content status with the fetched content
    - Skip any IDs that are empty or invalid
    """)

with fetch_col2:
    if st.button("🔄 Fetch Content", type="primary", use_container_width=True):
        with st.spinner("Fetching content from provided IDs..."):
            fetch_success = False
            
            # Count the number of IDs we have
            aroll_id_count = sum(1 for id in st.session_state.aroll_fetch_ids.values() if id)
            broll_id_count = sum(1 for id in st.session_state.broll_fetch_ids.values() if id)
            
            st.info(f"Found {aroll_id_count} A-Roll IDs and {broll_id_count} B-Roll IDs to fetch")
            
            # Process A-Roll IDs
            for segment_id, prompt_id in st.session_state.aroll_fetch_ids.items():
                if not prompt_id:
                    continue
                    
                # For A-Roll, we currently just simulate successful fetching
                st.session_state.content_status["aroll"][segment_id] = {
                    "status": "complete",
                    "file_path": f"fetched_aroll_{segment_id}_{prompt_id[:8]}.mp4",
                    "prompt_id": prompt_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                fetch_success = True
                
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

# Generate all content button
st.markdown("---")
st.subheader("Generate All Content")

if st.session_state.parallel_tasks["running"]:
    progress_value = st.session_state.parallel_tasks["completed"] / max(1, st.session_state.parallel_tasks["total"])
    st.progress(progress_value)
    st.info(f"Generating content... {st.session_state.parallel_tasks['completed']} of {st.session_state.parallel_tasks['total']} tasks completed")
    
    # Refresh the page every few seconds to update progress
    st.markdown("""
    <meta http-equiv="refresh" content="3">
    """, unsafe_allow_html=True)
else:
    if st.button("🚀 Start Parallel Generation", type="primary", use_container_width=True):
        # Capture all required data before starting the thread
        temp_segments = st.session_state.segments.copy() if hasattr(st.session_state, 'segments') and st.session_state.segments else []
        temp_broll_prompts = st.session_state.broll_prompts.copy() if hasattr(st.session_state, 'broll_prompts') and st.session_state.broll_prompts else {}
        temp_manual_upload = st.session_state.manual_upload if hasattr(st.session_state, 'manual_upload') else False
        temp_aroll_fetch_ids = st.session_state.aroll_fetch_ids.copy() if hasattr(st.session_state, 'aroll_fetch_ids') and st.session_state.aroll_fetch_ids else {}
        temp_broll_fetch_ids = st.session_state.broll_fetch_ids.copy() if hasattr(st.session_state, 'broll_fetch_ids') and st.session_state.broll_fetch_ids else {}
        temp_workflow_selection = st.session_state.workflow_selection.copy() if hasattr(st.session_state, 'workflow_selection') and st.session_state.workflow_selection else {"image": "default"}
        
        # Print debug info
        print(f"Debug - Starting content generation with {len(temp_segments)} segments")
        if len(temp_segments) > 0:
            # Log segment types
            a_roll_count = len([s for s in temp_segments if isinstance(s, dict) and s.get("type") == "A-Roll"])
            b_roll_count = len([s for s in temp_segments if isinstance(s, dict) and s.get("type") == "B-Roll"])
            print(f"Debug - Found {a_roll_count} A-Roll and {b_roll_count} B-Roll segments")
        
        # Check if segments is empty
        if not temp_segments:
            st.error("No segments found. Please ensure you have completed the Script Segmentation step.")
            st.stop()
        
        # Mark as running before starting the thread
        st.session_state.parallel_tasks["running"] = True
        
        # Start the content generation in a separate thread with captured data
        thread = threading.Thread(
            target=generate_content_parallel, 
            args=(temp_segments, temp_broll_prompts, temp_manual_upload, temp_aroll_fetch_ids, temp_broll_fetch_ids, temp_workflow_selection)
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
    prev_step_path="pages/4_BRoll_Prompts.py",
    next_step_path="pages/6_Video_Assembly.py") 

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