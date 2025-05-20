#!/usr/bin/env python3
import requests
import sys
import json
import os

# ComfyUI server addresses
COMFYUI_IMAGE_API_URL = "http://100.115.243.42:8000"
COMFYUI_VIDEO_API_URL = "http://100.86.185.76:8000"

def fetch_and_inspect_job(api_url, prompt_id):
    """Fetch job data and inspect its structure"""
    print(f"Fetching data for prompt ID {prompt_id} from {api_url}")
    
    try:
        # First check the queue
        queue_response = requests.get(f"{api_url}/queue", timeout=5)
        if queue_response.status_code == 200:
            queue_data = queue_response.json()
            print("\n=== QUEUE DATA ===")
            
            # Check running queue
            running_jobs = queue_data.get("queue_running", [])
            if running_jobs:
                print(f"Running jobs: {len(running_jobs)}")
                for job in running_jobs:
                    if job.get("prompt_id") == prompt_id:
                        print(f"Job found in running queue: {job}")
            else:
                print("No running jobs")
                
            # Check pending queue
            pending_jobs = queue_data.get("queue_pending", [])
            if pending_jobs:
                print(f"Pending jobs: {len(pending_jobs)}")
                for i, job in enumerate(pending_jobs):
                    if job.get("prompt_id") == prompt_id:
                        print(f"Job found in pending queue at position {i+1}: {job}")
            else:
                print("No pending jobs")
        else:
            print(f"Error fetching queue data: {queue_response.status_code}")
        
        # Now check history
        response = requests.get(f"{api_url}/history/{prompt_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n=== HISTORY DATA ===")
            if prompt_id in data:
                job_data = data[prompt_id]
                
                print(f"Top-level keys: {', '.join(job_data.keys())}")
                
                # Look at status field specifically
                if "status" in job_data:
                    print("\nStatus field:")
                    print(json.dumps(job_data["status"], indent=2))
                
                # Look at outputs field
                if "outputs" in job_data:
                    print("\nOutputs field:")
                    print(f"Number of output nodes: {len(job_data['outputs'])}")
                    
                    # Print the first output node as an example
                    for node_id, output in job_data["outputs"].items():
                        print(f"\nExample output node ({node_id}):")
                        print(f"Keys in output node: {', '.join(output.keys())}")
                        
                        if "images" in output:
                            print(f"Number of images: {len(output['images'])}")
                            if output['images']:
                                print(f"First image data: {output['images'][0]}")
                        
                        if "videos" in output:
                            print(f"Number of videos: {len(output['videos'])}")
                            if output['videos']:
                                print(f"First video data: {output['videos'][0]}")
                        break
                
                # Print the whole job data structure for inspection
                print("\n=== FULL JOB DATA ===")
                print(json.dumps(job_data, indent=2)[:2000])  # Print first 2000 chars to avoid flooding terminal
                print("...")
            else:
                print(f"Prompt ID {prompt_id} not found in history data")
                print(f"Available keys: {', '.join(data.keys())}")
        else:
            print(f"Error fetching history: {response.status_code}")
    
    except Exception as e:
        print(f"Error: {str(e)}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python inspect_job_data.py <prompt_id> [image|video]")
        print("Example: python inspect_job_data.py 5e14e67e-5b8f-4db7-a58b-3a16a992a1fc image")
        return
    
    prompt_id = sys.argv[1]
    
    # Default to image server if not specified
    server_type = "image"
    if len(sys.argv) >= 3:
        server_type = sys.argv[2].lower()
    
    api_url = COMFYUI_IMAGE_API_URL if server_type == "image" else COMFYUI_VIDEO_API_URL
    
    fetch_and_inspect_job(api_url, prompt_id)

if __name__ == "__main__":
    main() 