import streamlit as st
import os
import sys
import json
import requests
import time
import random
import threading
from pathlib import Path
from datetime import datetime, timedelta

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
    
    # Save content status to persist the prompt IDs
    if save_function and callable(save_function):
        save_function()
    
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
    
    # Create a key in session state to track if we need to rerun
    if "should_rerun_after_broll_gen" not in st.session_state:
        st.session_state.should_rerun_after_broll_gen = False
    
    # Check if we need to rerun based on previous submission
    if st.session_state.should_rerun_after_broll_gen:
        st.session_state.should_rerun_after_broll_gen = False
        time.sleep(0.5)  # Short delay to ensure state is updated
        st.rerun()
    
    # Add seconds per video configuration
    with broll_gen_col:
        st.subheader("B-Roll Generation Options")
        
        # Add auto-fetch configuration
        st.markdown("##### Auto-Fetch Configuration")
        
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown("""
            Set the average seconds it takes to generate one video. This will be used to calculate
            when auto-fetch attempts should be made.
            """)
            
        with col2:
            # Store this value in session state to persist across reruns
            if "seconds_per_video" not in st.session_state:
                st.session_state.seconds_per_video = 300
                
            seconds_per_video = st.number_input(
                "Seconds per Video",
                min_value=10,
                max_value=1800,
                value=st.session_state.seconds_per_video,
                step=10,
                help="Set the average time in seconds it takes to generate one video",
                key=f"seconds_per_video_{unique_key}"
            )
            
            # Update session state
            st.session_state.seconds_per_video = seconds_per_video
            
        st.markdown("---")
    
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
                # Show processing indicator
                with st.spinner("Submitting B-Roll jobs to ComfyUI..."):
                    # Generate B-roll sequentially
                    st.subheader("B-Roll Generation in Progress")
                    result = generate_broll_sequentially(broll_segments, project_path=project_path)
                    
                    # Save updated content status if function provided
                    if save_function and callable(save_function):
                        save_function()
                    
                    # Show summary
                    success_count = sum(1 for r in result.values() if r.get('status') == 'submitted')
                    st.success(f"Completed B-roll submission: {success_count} jobs out of {len(broll_segments)} segments.")
                    
                    # Schedule auto-fetch attempts
                    auto_fetch_config = schedule_auto_fetch(
                        broll_segments, 
                        project_path=project_path,
                        save_function=save_function,
                        seconds_per_video=seconds_per_video
                    )
                    
                    # Set flag for automatic page refresh
                    st.session_state.should_rerun_after_broll_gen = True
                    
                    # Create a refresh button in case auto-refresh doesn't work
                    st.info("Page will refresh automatically to show updated IDs... If it doesn't, click the button below.")
                    if st.button("🔄 Refresh Now", type="primary", key=f"manual_refresh_{unique_key}", use_container_width=True):
                        st.rerun()
                    
                    # Force a rerun after 1 second
                    time.sleep(1)
                    st.rerun()

# Function to schedule automatic fetches based on the number of segments and time per video
def schedule_auto_fetch(segments_data, api_url=None, project_path=None, save_function=None, seconds_per_video=300):
    """Schedule automatic fetches with increasing delays based on number of segments
    
    Args:
        segments_data: Dictionary of segments to process
        api_url: URL of the ComfyUI API
        project_path: Path to project directory
        save_function: Function to save content status
        seconds_per_video: Seconds it typically takes to generate one video
    """
    if api_url is None:
        api_url = "http://100.115.243.42:8000"
    
    # Get segment IDs
    segment_ids = list(segments_data.keys())
    num_segments = len(segment_ids)
    
    # Calculate wait time
    total_wait_time = num_segments * seconds_per_video
    
    # Status display placeholder
    status_container = st.empty()
    
    # Create a status message with estimates
    first_fetch_time = datetime.now() + timedelta(seconds=total_wait_time)
    second_fetch_time = first_fetch_time + timedelta(seconds=100)
    third_fetch_time = second_fetch_time + timedelta(seconds=200)
    
    status_container.info(f"""
    ### Auto-Fetch Scheduled:
    - First attempt: {first_fetch_time.strftime('%H:%M:%S')} (in {total_wait_time} seconds)
    - Second attempt: {second_fetch_time.strftime('%H:%M:%S')} (in {total_wait_time + 100} seconds)
    - Third attempt: {third_fetch_time.strftime('%H:%M:%S')} (in {total_wait_time + 300} seconds)
    
    You can still use the "Fetch Content" button at any time to check manually.
    """)
    
    # Get the prompt IDs from session state
    prompt_ids = {}
    if "broll_fetch_ids" in st.session_state:
        for segment_id in segment_ids:
            if segment_id in st.session_state.broll_fetch_ids:
                prompt_ids[segment_id] = st.session_state.broll_fetch_ids[segment_id]
    
    # Start the auto-fetch timer in a background thread
    thread = threading.Thread(
        target=_run_auto_fetch,
        args=(prompt_ids, api_url, project_path, save_function, status_container, 
              total_wait_time, [100, 200])
    )
    thread.daemon = True
    thread.start()
    
    # Return a message for confirmation
    return {
        "status": "scheduled",
        "first_fetch": total_wait_time,
        "second_fetch": total_wait_time + 100,
        "third_fetch": total_wait_time + 300
    }

# Background thread function for auto-fetch
def _run_auto_fetch(prompt_ids, api_url, project_path, save_function, status_container, 
                    initial_delay, additional_delays):
    """Run auto-fetch in background thread with multiple attempts
    
    Args:
        prompt_ids: Dictionary mapping segment_id to prompt_id
        api_url: URL of the ComfyUI API
        project_path: Path to project directory
        save_function: Function to save content status
        status_container: Streamlit container for status updates
        initial_delay: Seconds to wait before first fetch
        additional_delays: List of additional delays between subsequent fetches
    """
    # Sleep until first fetch time
    for i in range(initial_delay):
        # Update status every 10 seconds
        if i % 10 == 0:
            time_left = initial_delay - i
            status_container.info(f"### Auto-Fetch Status\nWaiting for first fetch in {time_left} seconds...")
        time.sleep(1)
    
    # Run first fetch
    status_container.warning("🔄 Running first auto-fetch...")
    fetch_results_1 = _perform_fetch(prompt_ids, api_url, project_path)
    
    # If not all fetches were successful and we have more attempts
    if fetch_results_1["not_ready"] and len(additional_delays) > 0:
        # Sleep until second fetch time
        for i in range(additional_delays[0]):
            if i % 10 == 0:
                time_left = additional_delays[0] - i
                status_container.info(f"### Auto-Fetch Status\nWaiting for second fetch in {time_left} seconds...")
            time.sleep(1)
            
        # Run second fetch but only for items that weren't ready
        status_container.warning("🔄 Running second auto-fetch...")
        prompt_ids_2 = {segment_id: prompt_id for segment_id, prompt_id in prompt_ids.items() 
                       if segment_id in fetch_results_1["not_ready"]}
        fetch_results_2 = _perform_fetch(prompt_ids_2, api_url, project_path)
        
        # If still not all fetches were successful and we have more attempts
        if fetch_results_2["not_ready"] and len(additional_delays) > 1:
            # Sleep until third fetch time
            for i in range(additional_delays[1]):
                if i % 10 == 0:
                    time_left = additional_delays[1] - i
                    status_container.info(f"### Auto-Fetch Status\nWaiting for third fetch in {time_left} seconds...")
                time.sleep(1)
                
            # Run third fetch but only for items that weren't ready
            status_container.warning("🔄 Running third auto-fetch...")
            prompt_ids_3 = {segment_id: prompt_id for segment_id, prompt_id in prompt_ids.items() 
                           if segment_id in fetch_results_2["not_ready"]}
            fetch_results_3 = _perform_fetch(prompt_ids_3, api_url, project_path)
            
            # Final status update
            if fetch_results_3["not_ready"]:
                status_container.error(f"⚠️ Auto-fetch complete. {len(fetch_results_3['not_ready'])} segments still not ready.")
            else:
                status_container.success("✅ All content successfully fetched!")
        else:
            # Final status update after second fetch
            if fetch_results_2["not_ready"]:
                status_container.error(f"⚠️ Auto-fetch complete. {len(fetch_results_2['not_ready'])} segments still not ready.")
            else:
                status_container.success("✅ All content successfully fetched!")
    else:
        # Final status update after first fetch
        if fetch_results_1["not_ready"]:
            status_container.error(f"⚠️ Auto-fetch complete. {len(fetch_results_1['not_ready'])} segments still not ready.")
        else:
            status_container.success("✅ All content successfully fetched!")
    
    # Save content status after all fetches
    if save_function and callable(save_function):
        try:
            save_function()
        except Exception as e:
            print(f"Error saving content status: {str(e)}")

# Helper function to perform fetch for each prompt ID
def _perform_fetch(prompt_ids, api_url, project_path):
    """Perform fetch for each prompt ID and return results
    
    Args:
        prompt_ids: Dictionary mapping segment_id to prompt_id
        api_url: URL of the ComfyUI API
        project_path: Path to project directory
        
    Returns:
        Dictionary with results summary
    """
    successful = []
    not_ready = []
    failed = []
    
    # If there's no session state, we can't update it
    if "content_status" not in st.session_state or "broll" not in st.session_state.content_status:
        return {"successful": [], "not_ready": list(prompt_ids.keys()), "failed": []}
        
    # Process each prompt ID
    for segment_id, prompt_id in prompt_ids.items():
        # Skip if prompt ID is empty
        if not prompt_id:
            continue
            
        # Set status to "fetching" to show progress
        st.session_state.content_status["broll"][segment_id] = {
            "status": "fetching",
            "prompt_id": prompt_id,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Fetch the content
        result = fetch_content_by_id(prompt_id, api_url)
        
        if result["status"] == "success":
            # Determine file extension based on content type
            content_type = result.get("type", "image")
            file_ext = "mp4" if content_type == "video" else "png"
            
            # Save the fetched content
            try:
                file_path = save_media_content(
                    result["content"], 
                    "broll",
                    segment_id,
                    file_ext,
                    project_path
                )
                
                st.session_state.content_status["broll"][segment_id] = {
                    "status": "complete",
                    "file_path": file_path,
                    "prompt_id": prompt_id,
                    "content_type": content_type,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                successful.append(segment_id)
            except Exception as e:
                st.session_state.content_status["broll"][segment_id] = {
                    "status": "error",
                    "message": f"Error saving content: {str(e)}",
                    "prompt_id": prompt_id,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
                failed.append(segment_id)
        elif result["status"] == "processing":
            # Content is still being generated
            st.session_state.content_status["broll"][segment_id] = {
                "status": "waiting",
                "message": "ComfyUI job still processing. Try again later.",
                "prompt_id": prompt_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            not_ready.append(segment_id)
        else:
            # Error fetching content
            st.session_state.content_status["broll"][segment_id] = {
                "status": "error",
                "message": result.get("message", "Unknown error fetching content"),
                "prompt_id": prompt_id,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            failed.append(segment_id)
    
    # Return summary of results
    return {
        "successful": successful,
        "not_ready": not_ready,
        "failed": failed
    } 