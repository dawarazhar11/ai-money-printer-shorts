#!/usr/bin/env python3
import sys
import os
import requests
import json
import time
import concurrent.futures
import base64
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ComfyUI server addresses (without /api prefix)
COMFYUI_IMAGE_SERVER = "http://100.115.243.42:8000"
COMFYUI_VIDEO_SERVER = "http://100.86.185.76:8000"

# Test workflow templates
IMAGE_WORKFLOW_TEMPLATE = "image_homepc.json"
VIDEO_WORKFLOW_TEMPLATE = "wan.json"

def load_workflow_template(template_file):
    """Load a workflow template file"""
    try:
        # Try to load from app root directory
        template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), template_file)
        with open(template_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # Try to load from current directory
        with open(template_file, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading workflow template: {e}")
        # Return a minimal test workflow if template can't be loaded
        return create_minimal_test_workflow()

def create_minimal_test_workflow():
    """Create a minimal test workflow if template can't be loaded"""
    # Simple text-to-image workflow
    if "image" in IMAGE_WORKFLOW_TEMPLATE.lower():
        return {
            "1": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 123456789,
                    "steps": 20,
                    "cfg": 7,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["2", 0],
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0]
                }
            },
            "2": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "dreamshaper_8.safetensors"
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "a beautiful mountain landscape, high quality, detailed",
                    "clip": ["2", 1]
                }
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "ugly, blurry, low quality",
                    "clip": ["2", 1]
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 1
                }
            },
            "6": {
                "class_type": "SaveImage",
                "inputs": {
                    "images": ["1", 0],
                    "filename_prefix": "ComfyUI_test"
                }
            }
        }
    else:
        # Simple animation workflow
        return {
            "1": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 123456789,
                    "steps": 20,
                    "cfg": 7,
                    "sampler_name": "euler_ancestral",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["2", 0],
                    "positive": ["3", 0],
                    "negative": ["4", 0],
                    "latent_image": ["5", 0]
                }
            },
            "2": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "dreamshaper_8.safetensors"
                }
            },
            "3": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "a beautiful mountain landscape with moving clouds, high quality, detailed",
                    "clip": ["2", 1]
                }
            },
            "4": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": "ugly, blurry, low quality",
                    "clip": ["2", 1]
                }
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": 512,
                    "height": 512,
                    "batch_size": 8
                }
            },
            "6": {
                "class_type": "SaveVideo",
                "inputs": {
                    "images": ["1", 0],
                    "filename_prefix": "ComfyUI_test_video",
                    "fps": 8
                }
            }
        }

def set_prompt_in_workflow(workflow, prompt, negative_prompt="ugly, blurry, low quality"):
    """Set the prompt in a workflow"""
    # Find CLIP nodes in the workflow
    for node_id, node in workflow.items():
        if "class_type" in node and node["class_type"] == "CLIPTextEncode" and "inputs" in node and "text" in node["inputs"]:
            # Check if this is a positive or negative prompt based on connections
            is_negative = False
            for other_node_id, other_node in workflow.items():
                if "inputs" in other_node and "negative" in other_node["inputs"]:
                    if other_node["inputs"]["negative"][0] == node_id:
                        is_negative = True
                        break
            
            # Set prompt text
            if is_negative:
                node["inputs"]["text"] = negative_prompt
            else:
                node["inputs"]["text"] = prompt
    
    return workflow

def submit_workflow(server_url, workflow):
    """Submit workflow to ComfyUI server"""
    try:
        prompt_url = f"{server_url}/prompt"
        
        response = requests.post(
            prompt_url,
            json={"prompt": workflow},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            prompt_id = data.get("prompt_id")
            print(f"Job submitted successfully, prompt ID: {prompt_id}")
            return prompt_id
        else:
            print(f"Error submitting job: HTTP {response.status_code}")
            print(response.text)
            return None
    except Exception as e:
        print(f"Error submitting workflow: {e}")
        return None

def check_job_status(server_url, prompt_id):
    """Check the status of a job"""
    try:
        history_url = f"{server_url}/history/{prompt_id}"
        response = requests.get(history_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            job_status = data.get("status", {}).get("status", "unknown")
            return job_status, data
        else:
            print(f"Error checking job status: HTTP {response.status_code}")
            return "error", None
    except Exception as e:
        print(f"Error checking job status: {e}")
        return "error", None

def wait_for_job_completion(server_url, prompt_id, max_wait_time=300):
    """Wait for job to complete"""
    start_time = time.time()
    
    while time.time() - start_time < max_wait_time:
        status, data = check_job_status(server_url, prompt_id)
        
        if status == "success":
            print(f"Job completed successfully in {time.time() - start_time:.1f} seconds")
            return True, data
        elif status == "error":
            print(f"Job failed")
            return False, data
        elif status == "pending" or status == "processing":
            print(f"Job still processing... ({time.time() - start_time:.1f}s)")
        else:
            print(f"Job status: {status}")
        
        # Check queue position
        try:
            queue_response = requests.get(f"{server_url}/queue", timeout=5)
            if queue_response.status_code == 200:
                queue_data = queue_response.json()
                running_jobs = queue_data.get("queue_running", [])
                pending_jobs = queue_data.get("queue_pending", [])
                
                for job in running_jobs:
                    if job.get("prompt_id") == prompt_id:
                        print(f"Job is currently running")
                        break
                
                for i, job in enumerate(pending_jobs):
                    if job.get("prompt_id") == prompt_id:
                        print(f"Job is waiting in queue at position {i+1}")
                        break
        except:
            pass
        
        time.sleep(5)
    
    print(f"Timed out after {max_wait_time} seconds")
    return False, None

def get_output_files(server_url, output_data):
    """Extract and download output files from job data"""
    files = []
    
    try:
        # Look for output nodes with images or videos
        for node_id, node_output in output_data.get("outputs", {}).items():
            if "images" in node_output:
                for img_data in node_output["images"]:
                    filename = img_data.get("filename")
                    if filename:
                        file_url = f"{server_url}/view?filename={filename}"
                        print(f"Found image output: {filename}")
                        files.append({"type": "image", "filename": filename, "url": file_url})
            
            # Check for videos, sometimes in "videos" or in "gifs" array
            for video_array in ["videos", "gifs"]:
                if video_array in node_output:
                    for video_data in node_output[video_array]:
                        filename = video_data.get("filename")
                        if filename:
                            file_url = f"{server_url}/view?filename={filename}"
                            print(f"Found video output: {filename}")
                            files.append({"type": "video", "filename": filename, "url": file_url})
    
    except Exception as e:
        print(f"Error extracting output files: {e}")
    
    return files

def download_file(file_info, output_dir="test_outputs"):
    """Download a file from the server"""
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Download the file
        response = requests.get(file_info["url"], timeout=60)
        
        if response.status_code == 200:
            output_path = os.path.join(output_dir, file_info["filename"])
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"Downloaded {file_info['type']}: {output_path}")
            return output_path
        else:
            print(f"Error downloading file: HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"Error downloading file: {e}")
        return None

def test_server(server_url, workflow_template, prompt, server_type):
    """Test a ComfyUI server with a workflow"""
    print(f"\n{'='*50}")
    print(f"Testing {server_type} server at {server_url}")
    print(f"{'='*50}")
    
    # Load workflow template
    workflow = load_workflow_template(workflow_template)
    
    # Set the prompt in the workflow
    workflow = set_prompt_in_workflow(workflow, prompt)
    
    # Submit the workflow
    prompt_id = submit_workflow(server_url, workflow)
    if not prompt_id:
        print(f"Failed to submit job to {server_type} server")
        return False, None
    
    # Wait for completion
    success, data = wait_for_job_completion(server_url, prompt_id)
    if not success:
        print(f"Job failed or timed out on {server_type} server")
        return False, None
    
    # Get output files
    files = get_output_files(server_url, data)
    if not files:
        print(f"No output files found from {server_type} server")
        return False, None
    
    # Download files
    output_dir = f"test_outputs_{server_type}"
    downloaded_files = []
    for file_info in files:
        file_path = download_file(file_info, output_dir)
        if file_path:
            downloaded_files.append(file_path)
    
    if downloaded_files:
        print(f"Successfully downloaded {len(downloaded_files)} files from {server_type} server")
        return True, downloaded_files
    else:
        print(f"Failed to download any files from {server_type} server")
        return False, None

def main():
    """Main test function"""
    print("ComfyUI API Test Script")
    print("Testing both image and video servers concurrently")
    
    image_prompt = "A beautiful mountain landscape with snow-capped peaks and clear blue sky, photography, 8k, detailed"
    video_prompt = "A beautiful mountain landscape with floating clouds and birds flying by, cinematic, 8k, detailed"
    
    # Run tests concurrently
    with concurrent.futures.ThreadPoolExecutor() as executor:
        image_future = executor.submit(
            test_server, 
            COMFYUI_IMAGE_SERVER, 
            IMAGE_WORKFLOW_TEMPLATE, 
            image_prompt, 
            "image"
        )
        
        video_future = executor.submit(
            test_server, 
            COMFYUI_VIDEO_SERVER, 
            VIDEO_WORKFLOW_TEMPLATE, 
            video_prompt, 
            "video"
        )
        
        # Wait for both tests to complete
        image_success, image_files = image_future.result()
        video_success, video_files = video_future.result()
    
    # Print summary
    print("\n\n========= Test Results Summary =========")
    print(f"Image server test: {'✅ SUCCESS' if image_success else '❌ FAILED'}")
    if image_files:
        print(f"  • Files generated: {len(image_files)}")
        for f in image_files:
            print(f"    - {os.path.basename(f)}")
    
    print(f"Video server test: {'✅ SUCCESS' if video_success else '❌ FAILED'}")
    if video_files:
        print(f"  • Files generated: {len(video_files)}")
        for f in video_files:
            print(f"    - {os.path.basename(f)}")
    
    if image_success and video_success:
        print("\n✅ All tests passed! Both servers are working correctly.")
    else:
        print("\n❌ Some tests failed. Please check the logs above for details.")

if __name__ == "__main__":
    main() 