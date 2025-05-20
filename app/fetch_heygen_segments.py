#!/usr/bin/env python3
import os
import argparse
from pathlib import Path
import time
import json
from utils.heygen_api import HeyGenAPI

def main():
    """
    Fetch existing videos from HeyGen API using predefined segment IDs
    """
    parser = argparse.ArgumentParser(description="Fetch HeyGen videos with specific segment IDs")
    parser.add_argument("--api_key", help="HeyGen API key", default=os.environ.get("HEYGEN_API_KEY", ""))
    parser.add_argument("--verbose", help="Enable verbose output", action="store_true")
    parser.add_argument("--download", help="Download videos to media/a-roll directory", action="store_true")
    parser.add_argument("--output", help="Path to save video report", default="media/a-roll/video_report.json")
    args = parser.parse_args()
    
    # Check if API key was provided
    if not args.api_key:
        print("Error: No API key provided. Please use --api_key or set HEYGEN_API_KEY environment variable.")
        return
    
    # Hardcoded segment IDs from the project
    segment_ids = [
        "5169ef5a328149a8b13c365ee7060106",  # SEG1
        "aed87db0234e4965825c7ee4c1067467",  # SEG2
        "e7d47355c21e4190bad8752c799343ee",  # SEG3
        "36064085e2a240768a8368bc6a911aea"   # SEG4
    ]
    
    # Initialize the HeyGen API client
    heygen_api = HeyGenAPI(args.api_key)
    
    # Create output directory if downloading
    if args.download:
        output_dir = Path("media/a-roll")
        output_dir.mkdir(parents=True, exist_ok=True)
        print(f"Videos will be saved to {output_dir.absolute()}")
    
    # Store video data for final report
    video_report = {
        "videos": [],
        "total_duration": 0,
        "successful_fetches": 0,
        "fetch_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "segment_mapping": {
            "SEG1": "5169ef5a328149a8b13c365ee7060106",
            "SEG2": "aed87db0234e4965825c7ee4c1067467",
            "SEG3": "e7d47355c21e4190bad8752c799343ee",
            "SEG4": "36064085e2a240768a8368bc6a911aea"
        }
    }
    
    # Fetch status for each segment ID
    for i, segment_id in enumerate(segment_ids):
        print(f"\n[{i+1}/{len(segment_ids)}] Checking segment ID: {segment_id}")
        
        # Get video status from HeyGen API
        status_response = heygen_api.check_video_status(segment_id)
        
        video_data = {
            "segment_id": segment_id,
            "segment_name": f"SEG{i+1}",
            "status": "error",
            "local_path": None,
            "duration": 0
        }
        
        if status_response["status"] == "success":
            data = status_response["data"]
            video_status = data.get("status", "unknown")
            video_url = data.get("video_url", "")
            
            # Extract duration if available
            if "raw_data" in data and "duration" in data["raw_data"]:
                video_data["duration"] = data["raw_data"]["duration"]
                video_report["total_duration"] += data["raw_data"]["duration"]
            
            print(f"  Status: {video_status}")
            
            if video_status.lower() in ["completed", "ready", "success", "done"]:
                if video_url:
                    print(f"  ✅ Video available: {video_url}")
                    video_data["status"] = "success"
                    video_report["successful_fetches"] += 1
                    
                    # Download the video if requested
                    if args.download and video_url:
                        output_path = f"media/a-roll/heygen_{segment_id}.mp4"
                        video_data["local_path"] = output_path
                        
                        print(f"  📥 Downloading to {output_path}...")
                        download_result = heygen_api.download_video(video_url, output_path)
                        
                        if download_result["status"] == "success":
                            print(f"  ✅ Downloaded to {output_path}")
                            video_data["downloaded"] = True
                        else:
                            print(f"  ❌ Download failed: {download_result['message']}")
                            video_data["downloaded"] = False
                else:
                    print(f"  ⚠️ Video completed but URL not available")
            else:
                print(f"  ⚠️ Video not ready (status: {video_status})")
                video_data["status"] = video_status
        else:
            print(f"  ❌ Failed to get status: {status_response.get('message', 'Unknown error')}")
        
        # Add video data to report
        video_report["videos"].append(video_data)
    
    # Save video report
    if args.output and video_report["successful_fetches"] > 0:
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, "w") as f:
            json.dump(video_report, f, indent=2)
        
        print(f"\nVideo report saved to {output_file}")
    
    # Print summary
    print("\n📊 Summary:")
    print(f"  ✅ Successfully fetched: {video_report['successful_fetches']}/{len(segment_ids)} videos")
    print(f"  🕒 Total duration: {video_report['total_duration']:.2f} seconds")
    print(f"  📁 Local storage: {Path('media/a-roll').absolute()}")
    print("\nDone!")

if __name__ == "__main__":
    main() 