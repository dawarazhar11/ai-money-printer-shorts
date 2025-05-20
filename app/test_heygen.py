#!/usr/bin/env python3
import os
import argparse
import json
from pathlib import Path
from utils.heygen_api import HeyGenAPI, test_heygen_api

def preview_segment_files(segment_ids, verbose=False):
    """
    Preview A-Roll segment files with the given IDs
    
    Args:
        segment_ids (list): List of segment IDs to preview
        verbose (bool): Whether to display more detailed information
        
    Returns:
        bool: True if all segments were found, False otherwise
    """
    media_dir = Path("media/a-roll")
    all_found = True
    results = []
    
    if not media_dir.exists():
        print(f"Media directory not found: {media_dir}")
        return False
    
    print("\n=== Previewing Segment Files ===")
    
    for i, segment_id in enumerate(segment_ids):
        print(f"\nSEG{i+1}: {segment_id}")
        
        # Check for exact match
        exact_match = list(media_dir.glob(f"*{segment_id}*.mp4"))
        
        # Check for files that might contain these IDs
        potential_matches = list(media_dir.glob(f"*.mp4"))
        potential_matches = [f for f in potential_matches if segment_id.lower() in f.name.lower()]
        
        if exact_match:
            file_path = exact_match[0]
            print(f"✅ Found file: {file_path.name}")
            
            # Get file information
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  - Size: {file_size_mb:.2f} MB")
            print(f"  - Path: {file_path}")
            
            # Try to get video duration if ffmpeg is available
            try:
                import subprocess
                result = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", 
                     "json", str(file_path)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                if result.returncode == 0:
                    data = json.loads(result.stdout)
                    duration = float(data["format"]["duration"])
                    print(f"  - Duration: {duration:.2f} seconds")
            except Exception as e:
                if verbose:
                    print(f"  - Could not get duration: {str(e)}")
            
            results.append({
                "segment_id": segment_id,
                "file_found": True,
                "file_path": str(file_path),
                "file_size_mb": file_size_mb
            })
        elif potential_matches:
            print(f"⚠️ Found potential matches:")
            for match in potential_matches[:5]:  # Show at most 5 matches
                print(f"  - {match.name}")
            
            # Use the first potential match
            file_path = potential_matches[0]
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            print(f"  - Using: {file_path.name} ({file_size_mb:.2f} MB)")
            
            results.append({
                "segment_id": segment_id,
                "file_found": True,
                "file_path": str(file_path),
                "file_size_mb": file_size_mb
            })
        else:
            print(f"❌ No matching file found")
            all_found = False
            results.append({
                "segment_id": segment_id,
                "file_found": False
            })
    
    return all_found, results

def fetch_existing_videos(api_key, video_ids, verbose=False):
    """
    Fetch existing videos from HeyGen API using their IDs
    
    Args:
        api_key (str): HeyGen API key
        video_ids (list): List of video IDs to fetch
        verbose (bool): Whether to display more detailed information
        
    Returns:
        tuple: (success, results)
    """
    client = HeyGenAPI(api_key)
    media_dir = Path("media/a-roll")
    media_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    success = True
    
    print("\n=== Fetching Existing Videos from HeyGen ===")
    
    for i, video_id in enumerate(video_ids):
        print(f"\nFetching SEG{i+1}: {video_id}")
        
        # Check video status first
        status_result = client.check_video_status(video_id)
        
        if status_result["status"] != "success":
            print(f"❌ Error checking video status: {status_result.get('message', 'Unknown error')}")
            if verbose:
                print(f"  - Full error: {status_result}")
            success = False
            results.append({
                "video_id": video_id,
                "success": False,
                "error": status_result.get("message", "Unknown error")
            })
            continue
        
        # Check if the video is ready
        video_status = status_result["data"].get("status", "").lower()
        
        if video_status not in ["ready", "completed", "done", "success"]:
            print(f"❌ Video is not ready. Current status: {video_status}")
            success = False
            results.append({
                "video_id": video_id,
                "success": False,
                "error": f"Video not ready. Status: {video_status}"
            })
            continue
        
        # Get the video URL
        video_url = status_result["data"].get("video_url", "")
        
        if not video_url:
            print(f"❌ No video URL found for video ID: {video_id}")
            success = False
            results.append({
                "video_id": video_id,
                "success": False,
                "error": "No video URL found"
            })
            continue
        
        # Download the video
        output_path = media_dir / f"heygen_{video_id}.mp4"
        download_result = client.download_video(video_url, str(output_path))
        
        if download_result["status"] != "success":
            print(f"❌ Error downloading video: {download_result.get('message', 'Unknown error')}")
            success = False
            results.append({
                "video_id": video_id,
                "success": False,
                "error": download_result.get("message", "Unknown error")
            })
            continue
        
        print(f"✅ Video downloaded successfully to: {output_path}")
        
        # Get file information
        try:
            file_size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f"  - Size: {file_size_mb:.2f} MB")
            
            # Try to get video duration if ffmpeg is available and verbose is enabled
            if verbose:
                try:
                    import subprocess
                    duration_result = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", 
                         "json", str(output_path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    if duration_result.returncode == 0:
                        data = json.loads(duration_result.stdout)
                        duration = float(data["format"]["duration"])
                        print(f"  - Duration: {duration:.2f} seconds")
                except Exception as e:
                    print(f"  - Could not get duration: {str(e)}")
        except Exception as e:
            print(f"  - Could not get file information: {str(e)}")
            file_size_mb = 0
        
        # Add result to list
        results.append({
            "video_id": video_id,
            "success": True,
            "file_path": str(output_path),
            "file_size_mb": file_size_mb
        })
    
    return success, results

def main():
    parser = argparse.ArgumentParser(description="Test the improved HeyGen API integration")
    parser.add_argument("--api_key", help="HeyGen API key", default=os.environ.get("HEYGEN_API_KEY", ""))
    parser.add_argument("--text", help="Test text to use", default="Welcome to AI Money Printer Shorts!")
    parser.add_argument("--test_only", help="Only test the connection without generating video", action="store_true")
    parser.add_argument("--avatar_id", help="Custom avatar ID to use")
    parser.add_argument("--voice_id", help="Custom voice ID to use")
    parser.add_argument("--preview", help="Preview existing segment files", action="store_true")
    parser.add_argument("--fetch", help="Fetch actual videos from HeyGen API", action="store_true")
    parser.add_argument("--download", help="Download existing videos from HeyGen using their IDs", action="store_true")
    parser.add_argument("--scripts", help="JSON file with scripts for each segment")
    parser.add_argument("--verbose", help="Show more detailed information", action="store_true")
    args = parser.parse_args()
    
    # Define the segment IDs
    segment_ids = [
        "5169ef5a328149a8b13c365ee7060106",  # SEG1
        "aed87db0234e4965825c7ee4c1067467",  # SEG2
        "e7d47355c21e4190bad8752c799343ee",  # SEG3
        "36064085e2a240768a8368bc6a911aea"   # SEG4
    ]
    
    # If preview mode is enabled, preview segment files and exit
    if args.preview:
        success, _ = preview_segment_files(segment_ids, args.verbose)
        return success
    
    # If download mode is enabled, download existing videos from HeyGen
    if args.download:
        if not args.api_key:
            print("❌ HeyGen API key not provided. Please provide with --api_key or set HEYGEN_API_KEY environment variable")
            return False
        
        success, _ = fetch_existing_videos(args.api_key, segment_ids, args.verbose)
        return success
    
    # If fetch mode is enabled, fetch videos from HeyGen API and exit
    if args.fetch:
        if not args.api_key:
            print("❌ HeyGen API key not provided. Please provide with --api_key or set HEYGEN_API_KEY environment variable")
            return False
        
        # Load scripts from file if provided
        scripts = None
        if args.scripts:
            try:
                with open(args.scripts, 'r') as f:
                    scripts_data = json.load(f)
                    if isinstance(scripts_data, list):
                        scripts = scripts_data
                    elif isinstance(scripts_data, dict) and "scripts" in scripts_data:
                        scripts = scripts_data["scripts"]
                    else:
                        print(f"⚠️ Invalid format in scripts file. Expected list or dict with 'scripts' key.")
            except Exception as e:
                print(f"❌ Error loading scripts file: {str(e)}")
                return False
        
        print("⚠️ Fetch mode is for generating new videos. Use --download to fetch existing videos.")
        return False
    
    if not args.api_key:
        print("❌ HeyGen API key not provided. Please provide with --api_key or set HEYGEN_API_KEY environment variable")
        return False
    
    # Test the API connection first
    print("=== Testing HeyGen API Connection ===")
    result = test_heygen_api(args.api_key, args.text)
    
    if result["status"] != "success":
        print(f"❌ HeyGen API test failed: {result.get('message', 'Unknown error')}")
        return False
    
    print("✅ HeyGen API connection test successful!")
    
    # Display available avatars and voices
    if "avatars" in result and result["avatars"]:
        print(f"\nFound {len(result['avatars'])} avatars:")
        for i, avatar in enumerate(result["avatars"][:5]):  # Display first 5
            avatar_id = avatar.get("id") or avatar.get("avatar_id")
            avatar_name = avatar.get("name") or avatar.get("avatar_name") or "Unknown"
            print(f"  {i+1}. {avatar_name}: {avatar_id}")
        if len(result["avatars"]) > 5:
            print(f"  ...and {len(result['avatars'])-5} more")
    
    if "voices" in result and result["voices"]:
        print(f"\nFound {len(result['voices'])} voices:")
        for i, voice in enumerate(result["voices"][:5]):  # Display first 5
            voice_id = voice.get("id") or voice.get("voice_id")
            voice_name = voice.get("name") or voice.get("voice_name") or "Unknown"
            print(f"  {i+1}. {voice_name}: {voice_id}")
        if len(result["voices"]) > 5:
            print(f"  ...and {len(result['voices'])-5} more")
    
    # If test only, exit here
    if args.test_only:
        return True
    
    # Generate a test video
    print("\n=== Generating Test Video ===")
    client = HeyGenAPI(args.api_key)
    
    # Generate the video
    video_result = client.generate_aroll(
        args.text,
        avatar_id=args.avatar_id,
        voice_id=args.voice_id
    )
    
    if video_result["status"] != "success":
        print(f"❌ Error generating video: {video_result.get('message', 'Unknown error')}")
        return False
    
    print("✅ Video generated successfully!")
    print(f"Video saved to: {video_result['file_path']}")
    
    # If we have multiple segments, show them all
    if "segments" in video_result:
        print(f"\nGenerated {len(video_result['segments'])} video segments:")
        for segment in video_result["segments"]:
            print(f"  Segment {segment['segment']}: {segment['file_path']}")
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!") 