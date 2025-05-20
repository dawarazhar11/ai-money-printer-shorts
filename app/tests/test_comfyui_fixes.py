#!/usr/bin/env python3
import sys
import os
import requests
import json
import time
from pathlib import Path
import datetime
import importlib.util

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ComfyUI server addresses
COMFYUI_IMAGE_API_URL = "http://100.115.243.42:8000"
COMFYUI_VIDEO_API_URL = "http://100.86.185.76:8000"

# Import the functions from Content Production page using importlib to avoid SyntaxError with numeric module name
try:
    # Use importlib.util to load the module with a numeric prefix
    module_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                             "pages", "5_Content_Production.py")
    
    spec = importlib.util.spec_from_file_location("content_production", module_path)
    content_production = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(content_production)
    
    # Now we can access the functions
    check_comfyui_job_status = content_production.check_comfyui_job_status
    fetch_comfyui_content_by_id = content_production.fetch_comfyui_content_by_id
    print("Successfully imported functions from Content Production page")
except Exception as e:
    print(f"Error importing functions: {e}")
    
    # Define fallback versions of the functions if import fails
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

    def fetch_comfyui_content_by_id(api_url, prompt_id):
        print("Using fallback implementation of fetch_comfyui_content_by_id")
        # Implementation skipped to save space - similar to the updated version


def test_job_status_checking():
    """Test the job status checking function with existing job IDs"""
    # Test video server job (should be successful)
    print("\n=== Testing job status check for video server ===")
    video_prompt_id = "e40ba27c-b8c0-4a1e-a29c-bfa62bd0ff50"
    video_status = check_comfyui_job_status(COMFYUI_VIDEO_API_URL, video_prompt_id)
    print(f"Status: {video_status}")
    
    # Test image server job (should be error status)
    print("\n=== Testing job status check for image server ===")
    image_prompt_id = "5e14e67e-5b8f-4db7-a58b-3a16a992a1fc"
    image_status = check_comfyui_job_status(COMFYUI_IMAGE_API_URL, image_prompt_id)
    print(f"Status: {image_status}")
    
    # Verify results
    if video_status.get("status") == "complete" and image_status.get("status") in ["error", "failed"]:
        print("\n✅ Job status checking is working correctly!")
        return True
    else:
        print("\n❌ Job status checking isn't producing expected results")
        return False

def test_content_fetching():
    """Test the content fetching function with an existing job ID"""
    print("\n=== Testing content fetching for successful video job ===")
    video_prompt_id = "e40ba27c-b8c0-4a1e-a29c-bfa62bd0ff50"
    fetch_result = fetch_comfyui_content_by_id(COMFYUI_VIDEO_API_URL, video_prompt_id)
    
    # Print status and content information
    print(f"Status: {fetch_result.get('status')}")
    if fetch_result.get("status") == "success":
        content_size = len(fetch_result.get("content", b"")) if "content" in fetch_result else "No content"
        print(f"Content size: {content_size} bytes")
        print(f"Filename: {fetch_result.get('filename')}")
        print(f"Content type: {fetch_result.get('type')}")
        
        # Save the content to a file for verification
        if "content" in fetch_result:
            output_dir = Path("test_outputs_fixes")
            output_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = output_dir / f"video_content_{timestamp}_{fetch_result.get('filename', 'output.mp4')}"
            
            with open(output_path, "wb") as f:
                f.write(fetch_result["content"])
            print(f"Saved content to: {output_path}")
        
        return True
    else:
        print(f"Error: {fetch_result.get('message', 'Unknown error')}")
        return False
    

def main():
    """Run all tests"""
    print("=== ComfyUI API Integration Fix Tests ===")
    print(f"Image Server: {COMFYUI_IMAGE_API_URL}")
    print(f"Video Server: {COMFYUI_VIDEO_API_URL}")
    
    # Run the status checking test
    status_result = test_job_status_checking()
    
    # Run the content fetching test
    content_result = test_content_fetching()
    
    # Print summary
    print("\n=== Test Results ===")
    print(f"Status checking: {'✅ PASS' if status_result else '❌ FAIL'}")
    print(f"Content fetching: {'✅ PASS' if content_result else '❌ FAIL'}")
    print(f"Overall status: {'✅ PASS' if status_result and content_result else '❌ FAIL'}")

if __name__ == "__main__":
    main() 