#!/usr/bin/env python3
import requests
import sys
import time
import json
import os
from pathlib import Path

# ComfyUI server addresses
COMFYUI_IMAGE_API_URL = "http://100.115.243.42:8000"
COMFYUI_VIDEO_API_URL = "http://100.86.185.76:8000"

def fetch_history(api_url, prompt_id):
    """Fetch history information for a prompt ID"""
    print(f"Fetching history for prompt ID: {prompt_id} from {api_url}")
    try:
        response = requests.get(f"{api_url}/history/{prompt_id}", timeout=10)
        print(f"Status code: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                print(f"Raw response structure contains these keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                if prompt_id in data:
                    job_keys = list(data[prompt_id].keys())
                    print(f"Job data contains these keys: {job_keys}")
                return data
            except json.JSONDecodeError:
                print("Error: Response not valid JSON")
                print("Content:", response.text[:200], "...")
                return None
        else:
            print(f"Error: HTTP {response.status_code}")
            print("Response:", response.text[:200])
            return None
    except Exception as e:
        print(f"Exception: {str(e)}")
        return None

def check_queue(api_url, prompt_id):
    """Check queue status"""
    print(f"Checking queue for prompt ID: {prompt_id}")
    try:
        response = requests.get(f"{api_url}/queue", timeout=5)
        if response.status_code == 200:
            data = response.json()
            
            # Look for our job in the running queue
            for job in data.get("queue_running", []):
                if job.get("prompt_id") == prompt_id:
                    print(f"Job found in running queue")
                    return True, "running"
            
            # Look for our job in the pending queue
            for i, job in enumerate(data.get("queue_pending", [])):
                if job.get("prompt_id") == prompt_id:
                    print(f"Job found in pending queue at position {i+1}")
                    return True, "pending"
                    
            print("Job not found in queue")
            return False, "not_found"
        else:
            print(f"Error checking queue: {response.status_code}")
            return False, "error"
    except Exception as e:
        print(f"Error checking queue: {e}")
        return False, "error"

def download_file(api_url, filename, output_path):
    """Download a file from ComfyUI server"""
    print(f"Downloading file: {filename}")
    try:
        # ComfyUI uses /view endpoint for files
        file_url = f"{api_url}/view?filename={filename}"
        
        response = requests.get(file_url, timeout=60)  # Longer timeout for larger files
        
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
                
            print(f"File successfully downloaded to {output_path}")
            return True
        else:
            print(f"Error downloading file: {response.status_code} - {response.text[:100]}")
            return False
    except Exception as e:
        print(f"Error downloading file: {str(e)}")
        return False

def extract_output_files(job_data):
    """Extract output files from job data"""
    print("Extracting output files...")
    files = []
    
    try:
        # Look for outputs (directly in the job_data or nested under "outputs")
        outputs = None
        if "outputs" in job_data:
            outputs = job_data["outputs"]
        
        if outputs:
            # Iterate through output nodes
            for node_id, node_output in outputs.items():
                if "images" in node_output:
                    for img_data in node_output["images"]:
                        filename = img_data.get("filename")
                        if filename:
                            files.append({"type": "image", "filename": filename})
                            print(f"Found image: {filename}")
                
                # Check for video outputs
                for video_array in ["videos", "gifs"]:
                    if video_array in node_output:
                        for video_data in node_output[video_array]:
                            filename = video_data.get("filename", "")
                            if filename:
                                files.append({"type": "video", "filename": filename})
                                print(f"Found video: {filename}")
        else:
            print("No outputs found in job data")
            
    except Exception as e:
        print(f"Error extracting output files: {str(e)}")
    
    return files

def detect_job_status(job_data):
    """Determine job status from ComfyUI job data"""
    # Check for status_str field in the status object (newer ComfyUI API format)
    if "status" in job_data and isinstance(job_data["status"], dict):
        if "status_str" in job_data["status"]:
            status_str = job_data["status"]["status_str"]
            print(f"Found status_str: {status_str}")
            return status_str
            
        if "completed" in job_data["status"]:
            if job_data["status"]["completed"] == True:
                return "success"
            
        # Look for messages indicating success or error
        if "messages" in job_data["status"]:
            for message in job_data["status"]["messages"]:
                if len(message) >= 2:
                    if message[0] == "execution_success":
                        return "success"
                    elif message[0] == "execution_error":
                        return "error"
    
    # Check for outputs directly, which indicates completion
    if "outputs" in job_data and job_data["outputs"]:
        return "success"
    
    # If we found nothing, return unknown
    return "unknown"

def fetch_and_download_content(api_url, prompt_id):
    """Fetch and download content for a given prompt ID"""
    print(f"\n{'='*50}")
    print(f"Testing content fetching from {api_url}")
    print(f"Prompt ID: {prompt_id}")
    print(f"{'='*50}")
    
    # Create output directory
    server_type = "image" if "115.243.42" in api_url else "video"
    output_dir = f"test_outputs_{server_type}"
    os.makedirs(output_dir, exist_ok=True)
    
    # First check if job is in queue
    in_queue, queue_status = check_queue(api_url, prompt_id)
    if in_queue:
        print(f"Job is still {queue_status} in queue, not ready to download yet")
        return False, None
    
    # Fetch history data
    history_data = fetch_history(api_url, prompt_id)
    if not history_data:
        print("Failed to fetch history data")
        return False, None
    
    # Check job status
    if prompt_id in history_data:
        job_data = history_data[prompt_id]
        
        # Determine job status using the helper function
        status = detect_job_status(job_data)
        print(f"Determined job status: {status}")
        
        if status == "success":
            # Extract output files
            files = extract_output_files(job_data)
            
            if not files:
                print("No output files found")
                return False, None
            
            # Download files
            downloaded_files = []
            for file_info in files:
                output_path = os.path.join(output_dir, file_info["filename"])
                success = download_file(api_url, file_info["filename"], output_path)
                if success:
                    downloaded_files.append({
                        "type": file_info["type"],
                        "path": output_path,
                        "filename": file_info["filename"]
                    })
            
            if downloaded_files:
                print(f"Successfully downloaded {len(downloaded_files)} files")
                return True, downloaded_files
            else:
                print("Failed to download any files")
                return False, None
        else:
            print(f"Job is not completed. Status: {status}")
            return False, None
    else:
        print(f"Prompt ID not found in history data")
        return False, None

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python fetch_comfyui_content.py <prompt_id> [image|video]")
        print("Example: python fetch_comfyui_content.py 5e14e67e-5b8f-4db7-a58b-3a16a992a1fc image")
        return
    
    prompt_id = sys.argv[1]
    
    # Default to image server if not specified
    server_type = "image"
    if len(sys.argv) >= 3:
        server_type = sys.argv[2].lower()
    
    api_url = COMFYUI_IMAGE_API_URL if server_type == "image" else COMFYUI_VIDEO_API_URL
    
    success, files = fetch_and_download_content(api_url, prompt_id)
    
    if success:
        print("\n✅ Content fetched and downloaded successfully!")
        for file in files:
            print(f"• {file['type'].upper()}: {file['path']}")
    else:
        print("\n❌ Failed to fetch or download content")

if __name__ == "__main__":
    main() 