import os
import requests
import json
import time
import tempfile
from pathlib import Path
import math
from utils.video_stitcher import download_video, stitch_video_segments
import base64
import re

def estimate_duration(text):
    """Estimate duration in seconds based on text length"""
    words = len(text.split())
    # Average speaking rate is about 150 words per minute
    return max(1, math.ceil(words / 2.5))

# Custom avatar ID lookup
def get_hardcoded_avatar_id():
    """Returns a hardcoded avatar ID that is known to work well with the API"""
    # For cat avatar
    return "Abigail_expressive_2024112501"  # Updated based on error logs

def fetch_avatar_ids(api_key):
    """
    Fetch available avatar IDs from HeyGen API.
    
    Args:
        api_key (str): HeyGen API key
        
    Returns:
        list: List of available avatar IDs
    """
    if not api_key:
        raise ValueError("HeyGen API key is required")
    
    # Set up headers for API request
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Try both API endpoints for different versions
    urls = [
        "https://api.heygen.com/v1/avatar.list",  # v1 API
        "https://api.heygen.com/v2/avatars"       # v2 API
    ]
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Extract avatar IDs based on API version
            if "data" in data and "avatars" in data["data"]:
                # v1 API format
                avatars = data["data"]["avatars"]
                return [avatar["avatar_id"] for avatar in avatars if "avatar_id" in avatar]
            elif "data" in data:
                # v2 API format might be different
                avatars = data["data"]
                return [avatar["id"] for avatar in avatars if "id" in avatar]
            
            return []
            
        except Exception as e:
            print(f"Error fetching avatars from {url}: {str(e)}")
    
    # If all endpoints fail, return an empty list
    return []

def fetch_voices(api_key):
    """
    Fetch available voices from HeyGen API.
    
    Args:
        api_key (str): HeyGen API key
        
    Returns:
        list: List of dictionaries with voice information
    """
    if not api_key:
        raise ValueError("HeyGen API key is required")
    
    # Set up headers for API request
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Try both API endpoints for different versions
    urls = [
        "https://api.heygen.com/v1/voice.list",  # v1 API
        "https://api.heygen.com/v2/voices"       # v2 API
    ]
    
    for url in urls:
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            
            # Extract voices based on API version
            if "data" in data and "voices" in data["data"]:
                # v1 API format
                return data["data"]["voices"]
            elif "data" in data:
                # v2 API format might be different
                return data["data"]
            
            return []
            
        except Exception as e:
            print(f"Error fetching voices from {url}: {str(e)}")
    
    # If all endpoints fail, raise an exception
    raise Exception("Failed to fetch voices from HeyGen API")

def check_video_status(video_id, api_key):
    """Poll the status of a video being generated"""
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Check multiple possible API endpoints based on the type of video
    v1_status_url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
    v2_status_url = f"https://api.heygen.com/v2/videos/{video_id}"
    v1_talking_photo_url = f"https://api.heygen.com/v1/talking_photo/{video_id}"
    
    try:
        # Try v1 talking_photo API first (for cat avatar)
        response = requests.get(v1_talking_photo_url, headers=headers)
        if response.status_code == 200:
            v1_data = response.json()
            # Convert talking_photo response format to standard format
            if "data" in v1_data and "status" in v1_data["data"]:
                return {
                    "data": {
                        "status": v1_data["data"]["status"],
                        "video_url": v1_data["data"].get("video_url", ""),
                        "error": v1_data.get("error", {}).get("message", "")
                    }
                }
        
        # Try v1 API (old API)
        response = requests.get(v1_status_url, headers=headers)
        if response.status_code == 200:
            return response.json()
            
        # If v1 fails, try v2 API (new API)
        response = requests.get(v2_status_url, headers=headers)
        if response.status_code == 200:
            v2_data = response.json()
            # Convert v2 response format to v1 format for compatibility
            return {
                "data": {
                    "status": v2_data.get("data", {}).get("status", "unknown"),
                    "video_url": v2_data.get("data", {}).get("video_url", ""),
                    "error": v2_data.get("error", {}).get("message", "")
                }
            }
        
        # If all fail, return the error
        return {"error": f"Failed to get status: {response.status_code} - {response.text}"}
    except Exception as e:
        return {"error": f"Exception checking video status: {str(e)}"}

def get_voice_id(voice_name):
    """Get voice ID from voice name"""
    # Define mapping of voice names to IDs
    voice_map = {
        "arthur_blackwood": "119caed25533477ba63822d5d1552d25",  # Updated based on error logs
        "matt": "9f8ff4eed26442168a8f2dc03c56e9ce",
        "sarah": "1582f2abbc114670b8999f22af70f09d",
        # Add more voice mappings as needed
    }
    return voice_map.get(voice_name, "119caed25533477ba63822d5d1552d25")  # Default to Arthur Blackwood

def generate_aroll(script, api_key, voice_name=None, avatar_id=None, background_color="#f6f6fc"):
    """
    Generate A-roll video using HeyGen API
    
    Args:
        script (str): Script text for the video
        api_key (str): HeyGen API key
        voice_name (str, optional): Name of the voice to use
        avatar_id (str, optional): ID of the avatar to use
        background_color (str, optional): Background color as hex code
        
    Returns:
        tuple: (video_id, error_message)
    """
    print(f"Generating video with avatar_id: {avatar_id}, voice_id: {voice_name}")
    
    # Use custom ID if provided, otherwise use the hardcoded ID
    if not avatar_id:
        avatar_id = get_hardcoded_avatar_id()
    
    # Determine if we're using a photo avatar
    is_photo_avatar = False  # Default to standard avatar
    
    # Get voice ID if we have a voice name
    voice_id = voice_name
    if not voice_id or voice_id.startswith("arthur"):
        voice_id = get_voice_id("arthur_blackwood")
    
    # Set up the API endpoint and headers
    url = "https://api.heygen.com/v2/video/generate"
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Prepare the payload
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": voice_id,
                    "speed": 1.0
                },
                "background": {
                    "type": "color",
                    "value": background_color
                }
            }
        ],
        "dimension": {
            "width": 1280,
            "height": 720
        },
        "title": "AI Generated Video",
        "caption": False,
        "settings": {
            "guidance": "Speak naturally with appropriate gestures."
        }
    }
    
    print(f"Sending payload:\n{json.dumps(payload, indent=2)}")
    
    try:
        # Send the request
        response = requests.post(url, headers=headers, json=payload)
        
        # Check if the request was successful
        if response.status_code == 200:
            data = response.json()
            if data.get("data"):
                video_id = data.get("data").get("video_id")
                return video_id, None
            else:
                error_message = f"No data in response: {data}"
                return None, error_message
        else:
            # Handle error response
            try:
                error_data = response.json()
                error_message = f"Error response from HeyGen API (status {response.status_code}):\n{json.dumps(error_data, indent=2)}"
                
                # Handle specific errors
                if "avatar_not_found" in str(error_data):
                    # Try with default avatar
                    print("Avatar not found, trying with default avatar")
                    return generate_aroll(script, api_key, voice_name, "Abigail_expressive_2024112501", background_color)
                elif "voice not found" in str(error_data).lower():
                    # Try with default voice
                    print("Voice not found, trying with default voice")
                    return generate_aroll(script, api_key, "119caed25533477ba63822d5d1552d25", avatar_id, background_color)
                    
            except:
                error_message = f"Error communicating with HeyGen API: {response.status_code} {response.reason}"
            
            return None, error_message
    except Exception as e:
        error_message = f"Exception calling HeyGen API: {str(e)}"
        return None, error_message

def fetch_video_by_id(video_id, api_key):
    """
    Fetch a video from HeyGen API using its ID.
    
    Args:
        video_id (str): HeyGen video ID to fetch
        api_key (str): HeyGen API key
        
    Returns:
        str: Path to the downloaded video file or None if failed
    """
    if not api_key:
        raise ValueError("HeyGen API key is required")
    
    if not video_id:
        raise ValueError("Video ID is required")
    
    # Create temporary directory for output if it doesn't exist
    output_dir = Path("temp/videos")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Set up headers for API request
    headers = {
        "X-Api-Key": api_key,
        "Content-Type": "application/json"
    }
    
    # Check the status of the video
    print(f"Fetching video with ID: {video_id}")
    status_data = check_video_status(video_id, api_key)
    
    if "error" in status_data:
        raise ValueError(f"Error checking video status: {status_data['error']}")
    
    # Check if the video is completed
    status = status_data.get("data", {}).get("status", "")
    if status != "completed":
        raise ValueError(f"Video is not completed. Current status: {status}")
    
    # Get the video URL
    video_url = status_data.get("data", {}).get("video_url")
    if not video_url:
        raise ValueError("No video URL returned in status response")
    
    print(f"Video found! URL: {video_url}")
    
    try:
        # Download the video
        download_resp = requests.get(video_url)
        download_resp.raise_for_status()
        
        # Save to a temporary file
        temp_file = output_dir / f"heygen_fetched_{video_id}.mp4"
        with open(temp_file, "wb") as f:
            f.write(download_resp.content)
        
        print(f"Downloaded video to: {temp_file}")
        
        # Use our download function to maintain consistency with the video storage system
        local_path = download_video(video_url, {"type": "a-roll", "id": video_id}, "heygen")
        
        return str(temp_file)
    except Exception as e:
        print(f"Error downloading video: {str(e)}")
        return None

def find_valid_avatar_id(api_key):
    """
    Find a valid avatar ID that can be used with the API.
    
    Args:
        api_key (str): HeyGen API key
        
    Returns:
        str: A valid avatar ID
    """
    # First try to fetch available avatars from the API
    try:
        valid_avatar_ids = fetch_avatar_ids(api_key)
        if valid_avatar_ids:
            print(f"Found {len(valid_avatar_ids)} avatars through the API")
            return valid_avatar_ids[0]
    except Exception as e:
        print(f"Could not fetch avatars: {str(e)}")
    
    # If API fetch fails, use hardcoded defaults
    print("Using hardcoded default avatars")
    valid_avatar_ids = [
        "Abigail_expressive_2024112501",  # Default Abigail
        "Adam_expressive_2024112501"      # Default Adam
    ]
    
    # Return the first ID in the list
    return valid_avatar_ids[0]

def generate_aroll_segments(segments, api_key, voice_name=None, avatar_id=None):
    """
    Generate multiple A-roll video segments using HeyGen API.
    
    Args:
        segments (list): List of segment dictionaries with 'content' key
        api_key (str): HeyGen API key
        voice_name (str, optional): Name of the voice to use (e.g., "fe612bdf07a94d5fa7b80bf1282937d1")
        avatar_id (str, optional): ID of the avatar to use (e.g., "35e0f2af72874fd6bc6e20cb74aebe72")
        
    Returns:
        list: List of dictionaries with segment info and paths to generated videos
    """
    if not api_key:
        raise ValueError("HeyGen API key is required")
    
    results = []
    
    # Process each segment
    for i, segment in enumerate(segments):
        if segment.get("type") != "a-roll":
            continue
            
        content = segment.get("content", "")
        description = segment.get("description", "")
        
        if not content.strip():
            continue
        
        # Get or create prompt
        prompt = segment.get("prompt", "Generate a professional talking head video with the script")
            
        # Check if there's a voice specified in the segment or use the provided voice_name
        segment_voice_name = None
        if voice_name:
            segment_voice_name = voice_name
        
        # Get avatar ID from segment or use the provided avatar_id
        segment_avatar_id = segment.get("avatar_id")
        if not segment_avatar_id and avatar_id:
            segment_avatar_id = avatar_id
        
        try:
            print(f"Generating A-roll segment {i+1}...")
            print(f"Content: {content[:50]}..." if len(content) > 50 else f"Content: {content}")
                
            # Generate the A-roll segment (remove prompt parameter as it's not accepted)
            video_id, error = generate_aroll(
                script=content,
                api_key=api_key,
                voice_name=segment_voice_name,
                avatar_id=segment_avatar_id
            )
            
            if error:
                print(f"Error from HeyGen API: {error}")
                raise ValueError(f"HeyGen API error: {error}")
                
            if not video_id:
                raise ValueError("No video ID returned from HeyGen API")
                
            # Fetch the video using the ID
            output_path = fetch_video_by_id(video_id, api_key)
            
            if not output_path:
                raise ValueError(f"Could not fetch video for ID: {video_id}")
                        
            # Add the result to our list
            results.append({
                "index": i,
                "type": "a-roll",
                "content": content,
                "description": description,
                "path": output_path,
                "api": "heygen",
                "video_id": video_id  # Store the video ID for future reference
            })
            
            print(f"Successfully generated A-roll segment {i+1} at {output_path}")
        
        except Exception as e:
            print(f"Error generating A-roll segment {i}: {str(e)}")
            # Continue with other segments
            
    return results

def split_and_generate_aroll(script, prompt, api_key, avatar_id=None, voice_id=None):
    """
    Split a script into A-ROLL segments and generate videos for each A-ROLL section.
    Then stitch them together into a single video.
    
    Args:
        script (str): The script text for the video 
        prompt (str): Additional prompt for guidance
        api_key (str): HeyGen API key
        avatar_id (str, optional): ID of the avatar to use. If None, a default will be used.
        voice_id (str, optional): ID of the voice to use. If None, a default will be used.
        
    Returns:
        str: Path to the final stitched video file
    """
    if not api_key:
        raise ValueError("HeyGen API key is required")
    
    # If no avatar_id provided, get a valid one from the API or use hardcoded ID
    if not avatar_id:
        # Use a hardcoded avatar ID that we know works
        avatar_id = get_hardcoded_avatar_id()
        print(f"Using hardcoded avatar ID: {avatar_id}")
    
    # If voice_id is not provided, use a default voice ID
    if not voice_id:
        voice_id = "119caed25533477ba63822d5d1552d25"  # Default voice ID
        print(f"Using default voice ID: {voice_id}")
    
    # Skip validation for hardcoded avatar IDs that we know work
    
    # IMPORTANT: Extract A-ROLL sections directly as separate segments
    print(f"Original script length: {len(script)} characters")
    print("Extracting A-ROLL segments directly from script...")
    
    # Pattern to split script into sections
    import re
    
    # Extract A-ROLL content only
    aroll_segments = []
    
    # Split by [A-ROLL] or [B-ROLL:] markers
    pattern = r'\[\s*(?:A-ROLL|B-ROLL:.*?)\s*\]'
    sections = re.split(pattern, script)
    markers = re.findall(pattern, script)
    
    # Make sure we have at least one marker
    if not markers:
        print("No [A-ROLL] or [B-ROLL] markers found. Treating entire script as A-roll.")
        aroll_segments.append({
            "content": script.strip(),
            "type": "a-roll"
        })
    else:
        # Go through each section and its preceding marker
        for i in range(len(sections) - 1):  # Skip the first section (before any marker)
            section_text = sections[i+1].strip()
            if not section_text:
                continue
                
            marker = markers[i].upper() if i < len(markers) else ""
            
            # If this is an A-ROLL section
            if "A-ROLL" in marker:
                aroll_segments.append({
                    "content": section_text,
                    "type": "a-roll"
                })
    
    print(f"Extracted {len(aroll_segments)} A-ROLL segments")
    
    # Prepare segments with required properties
    segments_to_generate = []
    for i, segment in enumerate(aroll_segments):
        # Verify each segment is under 1500 characters
        content = segment["content"]
        if len(content) > 1500:
            print(f"A-ROLL segment {i} exceeds 1500 characters ({len(content)} chars). Splitting further...")
            
            # Split this segment into smaller parts
            sentences = []
            # Split into sentences
            sentence_endings = re.finditer(r'[.!?]\s+', content)
            last_end = 0
            
            for match in sentence_endings:
                end = match.end()
                sentences.append(content[last_end:end])
                last_end = end
            
            # Add the final part if there's content left
            if last_end < len(content):
                sentences.append(content[last_end:])
            
            # Group sentences into segments under 1500 chars
            current_segment = ""
            for sentence in sentences:
                if len(current_segment) + len(sentence) <= 1500:
                    current_segment += sentence
                else:
                    # If current segment has content, add it
                    if current_segment:
                        segments_to_generate.append({
                            "type": "a-roll",
                            "content": current_segment,
                            "prompt": prompt,
                            "avatar_id": avatar_id,
                            "voice_id": voice_id,
                            "index": len(segments_to_generate)
                        })
                    
                    # Start a new segment
                    current_segment = sentence
            
            # Add the final segment if content left
            if current_segment:
                segments_to_generate.append({
                    "type": "a-roll",
                    "content": current_segment,
                    "prompt": prompt,
                    "avatar_id": avatar_id,
                    "voice_id": voice_id,
                    "index": len(segments_to_generate)
                })
        else:
            # This segment is already under 1500 chars
            segments_to_generate.append({
                "type": "a-roll",
                "content": content,
                "prompt": prompt,
                "avatar_id": avatar_id,
                "voice_id": voice_id,
                "index": i
            })
    
    print(f"Total segments to generate: {len(segments_to_generate)}")
    
    # Special case: if we have only one segment and it's short enough, use standard function
    if len(segments_to_generate) == 1 and len(segments_to_generate[0]["content"]) <= 1500:
        print("Using standard generation as we have only one segment under 1500 characters")
        try:
            result = generate_aroll(
                segments_to_generate[0]["content"], 
                prompt, 
                api_key, 
                avatar_id, 
                voice_id
            )
            return result
        except Exception as e:
            print(f"Error generating single A-roll segment: {str(e)}")
            raise ValueError(f"Error generating single A-roll segment: {str(e)}")
    
    # Generate videos for each segment
    try:
        generated_segments = generate_aroll_segments(
            segments_to_generate, 
            api_key, 
            voice_name=voice_id,  # Using voice_id as voice_name
            avatar_id=avatar_id
        )
        
        # If no segments were generated, raise an error
        if not generated_segments:
            raise ValueError("Failed to generate any video segments")
        
        print(f"Successfully generated {len(generated_segments)} A-roll segments")
        
        # Create a temporary file for the stitched output
        output_dir = Path("temp/videos")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"aroll_stitched_{int(time.time())}.mp4"
        
        # Extract the list of video paths from generated segments
        segment_paths = []
        for seg in generated_segments:
            if "path" in seg and os.path.exists(seg["path"]):
                segment_paths.append(seg["path"])
                print(f"Found valid segment path: {seg['path']}")
            else:
                print(f"Warning: Skipping segment with invalid path: {seg.get('path', 'No path specified')}")
                # Try to find the file in temp dirs as fallback
                segment_index = seg.get("index", 0)
                temp_dirs = [Path("temp/videos"), Path("temp_videos/heygen")]
                for temp_dir in temp_dirs:
                    if temp_dir.exists():
                        matching_files = list(temp_dir.glob(f"*segment_{segment_index}_*.mp4"))
                        if not matching_files:
                            matching_files = list(temp_dir.glob(f"*_{int(time.time() - 3600)}*.mp4"))
                        if matching_files:
                            segment_paths.append(str(matching_files[0]))
                            print(f"Found alternative path for segment {segment_index}: {matching_files[0]}")
                            break
        
        # If we couldn't find any valid segment paths, raise an error
        if not segment_paths:
            raise ValueError("No valid video segments found to stitch")
        
        # If we only have one segment, just return it (no need to stitch)
        if len(segment_paths) == 1:
            return segment_paths[0]
            
        # Stitch together the segments
        try:
            stitch_video_segments(segment_paths, str(output_path), crossfade_duration=0.3)
            return str(output_path)
        except Exception as e:
            print(f"Error stitching segments: {str(e)}")
            # If stitching fails, return the first segment
            return segment_paths[0]
            
    except Exception as e:
        print(f"Error in split_and_generate_aroll: {str(e)}")
        raise 