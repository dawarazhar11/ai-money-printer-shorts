import streamlit as st
import os
import sys
import json
import requests
import time
import random
from pathlib import Path
from datetime import datetime

# Import comfyui_api module for improved job handling
COMFYUI_API_AVAILABLE = False
try:
    import comfyui_api
    COMFYUI_API_AVAILABLE = True
except ImportError:
    print("Warning: comfyui_api module not found. Using direct HTTP requests instead.")

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

# Function to fetch content by ID
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
def save_media_content(content, segment_type, segment_id, file_extension, project_path=None):
    """Save media content to a file"""
    # If project_path is not provided, use current directory
    if project_path is None:
        project_path = Path(".")
        
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
def generate_broll_sequentially(segments_data, api_url=None, project_path=None):
    """Generate B-Roll content sequentially with proper tracking"""
    if api_url is None:
        api_url = "http://100.115.243.42:8000"
    
    # Track progress
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Store results
    results = {}
    total_segments = len(segments_data)
    
    # Track if AnimateDiff is available on the server
    animatediff_available = True
    
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
            
            # If we've already determined AnimateDiff isn't available, force image generation
            if is_video and not animatediff_available:
                st.warning("AnimateDiff not available on server. Falling back to image generation.")
                is_video = False
                
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
            try:
                # Use direct HTTP request instead of comfyui_api
                payload = {
                    "prompt": modified_workflow,
                    "client_id": client_id
                }
                
                # Submit the workflow to /prompt endpoint
                response = requests.post(
                    f"{api_url}/prompt",
                    json=payload,
                    timeout=30
                )
                
                # Check response
                if response.status_code == 200:
                    result_data = response.json()
                    prompt_id = result_data.get("prompt_id")
                    
                    if not prompt_id:
                        st.error("Failed to get prompt ID from response")
                        results[segment_id] = {"status": "error", "message": "Failed to get prompt ID from response"}
                        continue
                else:
                    error_msg = response.text
                    
                    # Check if this is an AnimateDiff error
                    if is_video and "AnimateDiff" in error_msg:
                        st.warning("AnimateDiff not available on server. Falling back to image generation.")
                        animatediff_available = False
                        
                        # Try again with image workflow
                        workflow = load_workflow("image")
                        if workflow is None:
                            st.error(f"Failed to load fallback image workflow for {segment_id}")
                            results[segment_id] = {"status": "error", "message": "Failed to load fallback workflow"}
                            continue
                            
                        # Modify workflow
                        modified_workflow = modify_workflow(workflow, params)
                        if modified_workflow is None:
                            st.error(f"Failed to modify fallback workflow for {segment_id}")
                            results[segment_id] = {"status": "error", "message": "Failed to modify fallback workflow"}
                            continue
                        
                        # Try again with image workflow
                        st.info("Retrying with image workflow...")
                        response = requests.post(
                            f"{api_url}/prompt",
                            json={"prompt": modified_workflow, "client_id": client_id},
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            result_data = response.json()
                            prompt_id = result_data.get("prompt_id")
                            
                            if not prompt_id:
                                st.error("Failed to get prompt ID from response")
                                results[segment_id] = {"status": "error", "message": "Failed to get prompt ID from response"}
                                continue
                                
                            content_type = "image"  # Update content type
                        else:
                            st.error(f"Failed to submit fallback job: {response.status_code} - {response.text}")
                            results[segment_id] = {"status": "error", "message": f"Fallback job submission failed: {response.status_code} - {response.text}"}
                            continue
                    else:
                        st.error(f"Failed to submit job: {response.status_code} - {error_msg}")
                        results[segment_id] = {"status": "error", "message": f"Job submission failed: {response.status_code} - {error_msg}"}
                        continue
                
                st.success(f"Job submitted with ID: {prompt_id}")
                
                # Store the prompt ID
                if "broll_fetch_ids" not in st.session_state:
                    st.session_state.broll_fetch_ids = {}
                st.session_state.broll_fetch_ids[segment_id] = prompt_id
                
                # Update content status to processing
                if "content_status" in st.session_state and "broll" in st.session_state.content_status:
                    st.session_state.content_status["broll"][segment_id] = {
                        "status": "processing",
                        "prompt_id": prompt_id,
                        "content_type": content_type,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                
                # Store successful submission in results
                results[segment_id] = {
                    "status": "submitted", 
                    "prompt_id": prompt_id,
                    "content_type": content_type
                }
                
                # IMPORTANT: Do not try to fetch content automatically
                st.info("Content generation job is now in queue. You can fetch the content later using the 'Fetch Content' button.")
                
            except Exception as e:
                st.error(f"Error submitting job: {str(e)}")
                results[segment_id] = {"status": "error", "message": f"Job submission error: {str(e)}"}
                continue
            
            # Add a separator between segments
            st.divider()
            
            # Wait a bit before next job to give ComfyUI time to recover
            if idx < total_segments - 1:
                time.sleep(1)
    
    # Update final progress
    progress_bar.progress(1.0)
    status_text.text(f"Completed submitting {total_segments} segments! Use 'Fetch Content' when jobs are complete.")
    
    # Provide a summary of submitted jobs
    st.success(f"Successfully submitted {sum(1 for r in results.values() if r.get('status') == 'submitted')} jobs to ComfyUI.")
    
    return results

# Define the B-Roll generation UI function
def render_broll_generation_section(unique_key="main", project_path=None, save_function=None):
    """Render the B-Roll generation section with a single 'Generate All B-Roll' button
    
    Args:
        unique_key: A unique identifier to append to widget keys to avoid duplicates
        project_path: Path to project directory
        save_function: Function to save content status
    """
    # Create a single column for B-roll generation (removing the two-column approach)
    broll_gen_col = st.container()
    
    with broll_gen_col:
        if st.button("🎨 Generate All B-Roll", type="primary", key=f"generate_broll_{unique_key}", use_container_width=True):
            # Capture all required data before starting
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
                result = generate_broll_sequentially(broll_segments, project_path=project_path)
                
                # Save updated content status if function provided
                if save_function and callable(save_function):
                    save_function()
                
                # Show summary
                success_count = sum(1 for r in result.values() if r.get('status') == 'success')
                st.success(f"Completed B-roll generation: {success_count} successful out of {len(broll_segments)} segments.")
                
                # Mark step as complete if all segments succeeded and mark_step_complete is available
                if success_count == len(broll_segments):
                    if 'mark_step_complete' in globals():
                        mark_step_complete('content_production')
                    st.balloons()  # Add some fun! 