#!/usr/bin/env python3
"""
Test script for AI Money Printer Shorts features:
1. Generate test A-Roll and B-Roll files 
2. Test HeyGen API integration
"""

import os
import sys
import argparse
from pathlib import Path

# Add the app directory to the Python path
app_dir = os.path.dirname(os.path.abspath(__file__))
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)

def generate_test_videos():
    """Generate test videos for A-Roll and B-Roll segments"""
    try:
        from utils.test_data import generate_test_aroll_files, generate_test_broll_files
        
        project_path = app_dir
        print("\n=== Generating Test Videos ===")
        print(f"Project path: {project_path}")
        
        # Generate A-Roll files
        print("\nGenerating A-Roll files...")
        aroll_files = generate_test_aroll_files(project_path)
        print(f"Created {len(aroll_files)} A-Roll files:")
        for file in aroll_files:
            print(f"  - {file}")
        
        # Generate B-Roll files
        print("\nGenerating B-Roll files...")
        broll_files = generate_test_broll_files(project_path, num_segments=3)
        print(f"Created {len(broll_files)} B-Roll files:")
        for file in broll_files:
            print(f"  - {file}")
        
        # Update content status
        update_content_status(aroll_files, broll_files)
        
        return True
    except Exception as e:
        print(f"Error generating test videos: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def update_content_status(aroll_files, broll_files):
    """Update content status file with the generated test files"""
    try:
        import json
        from datetime import datetime
        
        project_path = Path(app_dir)
        status_file = project_path / "config" / "user_data" / "my_short_video" / "content_status.json"
        
        # Create directory if it doesn't exist
        status_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize content status
        content_status = {
            "aroll": {},
            "broll": {}
        }
        
        # Try to load existing content status
        if status_file.exists():
            try:
                with open(status_file, "r") as f:
                    content_status = json.load(f)
            except:
                pass
        
        # Update A-Roll status
        for file_path in aroll_files:
            # Extract segment ID from filename
            file_name = os.path.basename(file_path)
            parts = file_name.split("_")
            if len(parts) >= 3 and parts[0] == "fetched" and parts[1] == "aroll":
                segment_id = parts[2]
                content_status["aroll"][segment_id] = {
                    "status": "complete",
                    "file_path": file_path,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        
        # Update B-Roll status
        for file_path in broll_files:
            # Extract segment ID from filename
            file_name = os.path.basename(file_path)
            parts = file_name.split("_")
            if len(parts) >= 3 and parts[0] == "generated" and parts[1] == "broll":
                segment_id = parts[2].split(".")[0]  # Remove file extension
                content_status["broll"][segment_id] = {
                    "status": "complete",
                    "file_path": file_path,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
        
        # Save updated content status
        with open(status_file, "w") as f:
            json.dump(content_status, f, indent=4)
        
        print(f"\nUpdated content status file: {status_file}")
        return True
    except Exception as e:
        print(f"Error updating content status: {str(e)}")
        return False

def test_heygen_api(api_key):
    """Test HeyGen API integration"""
    try:
        from utils.heygen_api import test_heygen_api as run_heygen_test
        
        print("\n=== Testing HeyGen API ===")
        
        # Run the API test
        print("Connecting to HeyGen API...")
        result = run_heygen_test(api_key)
        
        if result["status"] == "success":
            print("✅ HeyGen API test successful!")
            
            # Print connection information
            conn_test = result.get("connection_test", {})
            print(f"Connection: {conn_test.get('message', 'Unknown')}")
            
            # Print avatar information
            avatars = result.get("avatars", {}).get("data", {}).get("data", [])
            if avatars:
                print(f"Found {len(avatars)} avatars")
                for i, avatar in enumerate(avatars[:3]):  # Show up to 3 avatars
                    print(f"  {i+1}. {avatar.get('name', 'Unknown')} (ID: {avatar.get('id', 'Unknown')})")
                if len(avatars) > 3:
                    print(f"  ... and {len(avatars) - 3} more")
            
            # Print video information
            completion = result.get("completion", {})
            if completion.get("status") == "success":
                video_data = completion.get("data", {}).get("data", {})
                video_url = video_data.get("video_url", "Unknown")
                print(f"Test video created successfully: {video_url}")
                
                # Download the video
                from utils.heygen_api import HeyGenAPI
                client = HeyGenAPI(api_key)
                output_path = os.path.join(app_dir, "media", "heygen_test.mp4")
                download_result = client.download_video(video_url, output_path)
                
                if download_result["status"] == "success":
                    print(f"Video downloaded to: {download_result['file_path']}")
                else:
                    print(f"Failed to download video: {download_result.get('message', 'Unknown error')}")
            else:
                print(f"Video generation failed: {completion.get('message', 'Unknown error')}")
        else:
            print(f"❌ HeyGen API test failed: {result.get('message', 'Unknown error')}")
        
        return result["status"] == "success"
    except Exception as e:
        print(f"Error testing HeyGen API: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description="Test AI Money Printer Shorts features")
    parser.add_argument("--videos", action="store_true", help="Generate test videos")
    parser.add_argument("--heygen", help="Test HeyGen API with the provided API key")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    if not (args.videos or args.heygen or args.all):
        parser.print_help()
        return
    
    if args.videos or args.all:
        success = generate_test_videos()
        if not success:
            print("❌ Failed to generate test videos")
    
    if args.heygen or args.all:
        api_key = args.heygen
        if args.all and not api_key:
            api_key = os.environ.get("HEYGEN_API_KEY", "")
            if not api_key:
                print("❌ HeyGen API key not provided. Use --heygen <api_key> or set HEYGEN_API_KEY environment variable")
                return
        
        success = test_heygen_api(api_key)
        if not success:
            print("❌ Failed to test HeyGen API")

if __name__ == "__main__":
    main() 