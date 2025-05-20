import os
import requests
import json
import time
from pathlib import Path
import base64
import re
import math

class HeyGenAPI:
    """
    Class to interact with the HeyGen API for video generation
    """
    
    def __init__(self, api_key):
        """
        Initialize the HeyGen API client
        
        Args:
            api_key: HeyGen API key (may be Base64 encoded)
        """
        # Store the original API key
        self.original_api_key = api_key
        
        # Try to decode if it's Base64 encoded
        try:
            # Check if it looks like Base64 (no special chars except maybe = at end)
            if all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in api_key):
                try:
                    # Handle potential padding issues
                    padding = 4 - (len(api_key) % 4) if len(api_key) % 4 else 0
                    padded_key = api_key + ("=" * padding)
                    
                    # Some API keys are already decoded but still Base64-like
                    decoded_key = base64.b64decode(padded_key).decode('utf-8')
                    if decoded_key and len(decoded_key) > 10:  # Sanity check - decoded key should be substantial
                        # Check if decoded key has a valid format (often contains dash or hyphen)
                        if '-' in decoded_key or '_' in decoded_key:
                            self.api_key = decoded_key
                            print(f"Successfully decoded Base64 API key")
                        else:
                            self.api_key = api_key  # Fallback to original if decode results in something weird
                    else:
                        self.api_key = api_key  # Fallback to original if decode results in something weird
                except Exception as e:
                    # If decode fails, use as-is
                    print(f"Base64 decode failed: {str(e)}, using original key")
                    self.api_key = api_key
            else:
                self.api_key = api_key
        except Exception as e:
            # If any error in decoding, use as-is
            print(f"Exception during API key processing: {str(e)}")
            self.api_key = api_key
            
        # Base URLs for V1 and V2 API
        self.v1_base_url = "https://api.heygen.com/v1"
        self.v2_base_url = "https://api.heygen.com/v2"
        self.alt_base_url = "https://api.heygen.ai/v1"  # Alternative domain
        self.base_url = self.v2_base_url  # Default to v2
        
        # Log the API key we're using (last few characters for debugging)
        if len(self.api_key) > 10:
            print(f"Using API key ending with: ...{self.api_key[-10:]}")
        if len(self.original_api_key) > 10:
            print(f"Original API key ends with: ...{self.original_api_key[-10:]}")
        
        # Try different authentication methods and formats
        self.headers_variants = [
            # Original key in different header formats
            {
                "X-Api-Key": self.original_api_key,
                "Content-Type": "application/json"
            },
            {
                "Authorization": f"Bearer {self.original_api_key}",
                "Content-Type": "application/json"
            },
            {
                "Api-Key": self.original_api_key,
                "Content-Type": "application/json"
            },
            # Decoded key in different header formats (if different from original)
            {
                "X-Api-Key": self.api_key,
                "Content-Type": "application/json"
            },
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            {
                "Api-Key": self.api_key,
                "Content-Type": "application/json"
            },
            # Try without content-type header
            {
                "X-Api-Key": self.original_api_key
            },
            {
                "X-Api-Key": self.api_key
            },
            # Try different capitalization
            {
                "x-api-key": self.original_api_key,
                "Content-Type": "application/json"
            },
            {
                "x-api-key": self.api_key,
                "Content-Type": "application/json"
            }
        ]
        
        # Default to the first variant - we'll test all variants later
        self.headers = self.headers_variants[0]
        
        # Test all auth variants to find the working one
        self.test_all_auth_variants()
    
    def get_hardcoded_avatar_id(self):
        """Returns a hardcoded avatar ID that is known to work well with the API"""
        return "Abigail_expressive_2024112501"  # Default avatar that works
    
    def get_voice_id(self, voice_name=None):
        """Get voice ID from voice name or return a default one"""
        # Define mapping of voice names to IDs
        voice_map = {
            "arthur_blackwood": "119caed25533477ba63822d5d1552d25",
            "matt": "9f8ff4eed26442168a8f2dc03c56e9ce",
            "sarah": "1582f2abbc114670b8999f22af70f09d",
        }
        
        if voice_name and voice_name in voice_map:
            return voice_map[voice_name]
        elif voice_name and "arthur" in voice_name.lower():
            return voice_map["arthur_blackwood"]
        
        # Default to Arthur Blackwood
        return "119caed25533477ba63822d5d1552d25"
    
    def test_all_auth_variants(self):
        """
        Test all authentication header variants to find a working one
        
        Returns:
            dict: Response indicating success or failure
        """
        print(f"Testing all authentication variants...")
        
        # Define all API endpoints to test
        endpoints = [
            # v2 endpoints
            f"{self.v2_base_url}/status",
            f"{self.v2_base_url}/avatars",
            # v1 endpoints
            f"{self.v1_base_url}/voice.list",
            f"{self.v1_base_url}/status",
            # Alternative domain
            f"{self.alt_base_url}/status",
        ]
        
        # Try each combination of headers and endpoints
        for i, headers in enumerate(self.headers_variants):
            print(f"Trying auth variant {i+1}/{len(self.headers_variants)}")
            
            for endpoint in endpoints:
                try:
                    print(f"  Testing {endpoint}")
                    response = requests.get(
                        endpoint, 
                        headers=headers,
                        timeout=5
                    )
                    
                    # Even if not 200, if we got a JSON response, that's a good sign
                    if response.status_code != 401:  # Not unauthorized
                        # Try to parse as JSON
                        try:
                            content = response.json()
                            print(f"  ✅ Received valid JSON response from {endpoint} with status {response.status_code}")
                            print(f"  Response: {content}")
                            
                            # Store the working endpoint and headers
                            self.base_url = endpoint.split('/status')[0] if '/status' in endpoint else endpoint.split('/voice.list')[0]
                            self.headers = headers
                            
                            print(f"  Successfully authenticated! Using base URL: {self.base_url}")
                            return {
                                "status": "success",
                                "message": f"Successfully authenticated with variant {i+1}",
                                "headers": headers,
                                "base_url": self.base_url,
                                "response": content
                            }
                        except:
                            print(f"  Received non-JSON response with status {response.status_code}")
                except Exception as e:
                    print(f"  Error testing {endpoint}: {str(e)}")
        
        # If all combinations fail, return error
        return {
            "status": "error",
            "message": "Failed to authenticate with all header variants"
        }
    
    def test_connection(self):
        """
        Test the connection to the HeyGen API
        
        Returns:
            dict: Response from the API
        """
        # First try all auth variants to find a working one
        auth_test = self.test_all_auth_variants()
        if auth_test["status"] == "success":
            return auth_test
            
        # If no variant worked, try one more direct test with the default
        try:
            # Print useful debug info
            print(f"Trying to connect to {self.base_url}/status with API key: {self.api_key[:10]}...")
            
            response = requests.get(
                f"{self.base_url}/status",
                headers=self.headers,
                timeout=10
            )
            
            # Even if it's an error response, we want to see the content
            print(f"Response status: {response.status_code}")
            try:
                content = response.json()
                print(f"Response content: {content}")
            except:
                print(f"Raw response: {response.content[:100]}")
            
            response.raise_for_status()
            
            return {
                "status": "success",
                "message": "Successfully connected to HeyGen API",
                "response": response.json() if response.content else {}
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "message": f"Error connecting to HeyGen API: {str(e)}",
                "error": str(e)
            }
    
    def list_avatars(self):
        """
        List available avatars
        
        Returns:
            dict: List of avatars
        """
        # Try both API versions
        for base_url in [self.v2_base_url, self.v1_base_url]:
            try:
                # Use the appropriate endpoint for the API version
                if base_url == self.v1_base_url:
                    url = f"{base_url}/avatar.list"
                else:
                    url = f"{base_url}/avatars"
                
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                # Extract avatars based on API version
                if "data" in data and "avatars" in data["data"]:
                    # v1 API format
                    return {
                        "status": "success",
                        "data": data["data"]["avatars"]
                    }
                elif "data" in data:
                    # v2 API format
                    return {
                        "status": "success",
                        "data": data["data"]
                    }
            except requests.exceptions.RequestException as e:
                print(f"Error listing avatars from {base_url}: {str(e)}")
        
        # Return error if both API versions failed
        return {
            "status": "error",
            "message": "Error listing avatars from all API versions"
        }
    
    def list_voices(self):
        """
        List available voices
        
        Returns:
            dict: List of voices
        """
        # Try both API versions
        for base_url in [self.v2_base_url, self.v1_base_url]:
            try:
                # Use the appropriate endpoint for the API version
                if base_url == self.v1_base_url:
                    url = f"{base_url}/voice.list"
                else:
                    url = f"{base_url}/voices"
                
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                # Extract voices based on API version
                if "data" in data and "voices" in data["data"]:
                    # v1 API format
                    return {
                        "status": "success",
                        "data": data["data"]["voices"]
                    }
                elif "data" in data:
                    # v2 API format
                    return {
                        "status": "success",
                        "data": data["data"]
                    }
            except requests.exceptions.RequestException as e:
                print(f"Error listing voices from {base_url}: {str(e)}")
        
        # Return error if both API versions failed
        return {
            "status": "error",
            "message": "Error listing voices from all API versions"
        }
    
    def create_talking_video(self, text, avatar_id=None, voice_id=None, background_color="#f6f6fc"):
        """
        Create a talking video using an avatar
        
        Args:
            text: Text to convert to speech
            avatar_id: ID of the avatar to use (optional, uses default if not provided)
            voice_id: ID of the voice to use (optional, uses default if not provided)
            background_color: Background color as hex code
            
        Returns:
            dict: Response with video ID
        """
        # Use default avatar and voice if not provided
        if not avatar_id:
            avatar_id = self.get_hardcoded_avatar_id()
        
        if not voice_id:
            voice_id = self.get_voice_id()
        
        print(f"Creating talking video with avatar_id: {avatar_id}, voice_id: {voice_id}")
        print(f"Text: {text[:50]}..." if len(text) > 50 else f"Text: {text}")
        
        try:
            # Use v2 API endpoint
            url = f"{self.v2_base_url}/video/generate"
            
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
                            "input_text": text,
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
            
            print(f"Sending payload to {url}")
            response = requests.post(url, json=payload, headers=self.headers)
            
            # Check if the request was successful
            if response.status_code == 200:
                data = response.json()
                if data.get("data"):
                    video_id = data.get("data").get("video_id")
                    return {
                        "status": "success",
                        "message": "Successfully created talking video",
                        "video_id": video_id,
                        "data": data
                    }
                else:
                    error_message = f"No data in response: {data}"
                    return {
                        "status": "error",
                        "message": error_message
                    }
            else:
                # Handle error response
                try:
                    error_data = response.json()
                    error_message = f"Error response from HeyGen API (status {response.status_code}):\n{json.dumps(error_data, indent=2)}"
                    
                    # Handle specific errors
                    if "avatar_not_found" in str(error_data):
                        # If avatar not found, try with default avatar
                        if avatar_id != self.get_hardcoded_avatar_id():
                            print("Avatar not found, trying with default avatar")
                            return self.create_talking_video(text, self.get_hardcoded_avatar_id(), voice_id, background_color)
                    elif "voice not found" in str(error_data).lower():
                        # If voice not found, try with default voice
                        if voice_id != self.get_voice_id():
                            print("Voice not found, trying with default voice")
                            return self.create_talking_video(text, avatar_id, self.get_voice_id(), background_color)
                except:
                    error_message = f"Error communicating with HeyGen API: {response.status_code} {response.reason}"
                
                # Try v1 API as fallback
                try:
                    print(f"Trying v1 API as fallback")
                    url = f"{self.v1_base_url}/talking_photo"
                    
                    # Simplified payload for v1 API
                    v1_payload = {
                        "avatar_url": "",  # Will use default avatar from HeyGen
                        "avatar_id": avatar_id,
                        "voice_id": voice_id,
                        "text": text,
                        "voice_type": "text",
                        "background_color": background_color
                    }
                    
                    response = requests.post(url, json=v1_payload, headers=self.headers)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("data"):
                            video_id = data.get("data").get("video_id")
                            return {
                                "status": "success",
                                "message": "Successfully created talking video using v1 API",
                                "video_id": video_id,
                                "data": data
                            }
                    
                    print(f"V1 API fallback failed: {response.status_code} - {response.text}")
                except Exception as e:
                    print(f"V1 API fallback error: {str(e)}")
                
                return {
                    "status": "error",
                    "message": error_message
                }
        except Exception as e:
            error_message = f"Exception calling HeyGen API: {str(e)}"
            return {
                "status": "error",
                "message": error_message
            }
    
    def check_video_status(self, video_id):
        """
        Check the status of a video
        
        Args:
            video_id: ID of the video to check
            
        Returns:
            dict: Response from the API
        """
        if not video_id:
            return {
                "status": "error",
                "message": "No video ID provided"
            }
        
        print(f"Checking status for video ID: {video_id}")
        
        # Primary URL - the exact endpoint format from documentation
        primary_url = f"{self.v1_base_url}/video_status.get?video_id={video_id}"
        
        # Fallback URLs to try if primary fails
        fallback_urls = [
            f"{self.v2_base_url}/videos/{video_id}",  # v2 API format
            f"{self.v1_base_url}/videos/{video_id}",  # v1 API format
            f"{self.alt_base_url}/video_status.get?video_id={video_id}",  # Alternative domain with correct format
            f"{self.alt_base_url}/videos/{video_id}",  # Alternative domain
        ]
        
        # First, try the primary URL with the most likely header format
        primary_headers = {
            "accept": "application/json",
            "x-api-key": self.original_api_key
        }
        
        try:
            print(f"Trying primary endpoint: {primary_url}")
            print(f"Using headers: {primary_headers}")
            
            response = requests.get(primary_url, headers=primary_headers, timeout=10)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    response_data = response.json()
                    print(f"Response data: {response_data}")
                    
                    # Extract data from the response
                    if "data" in response_data and isinstance(response_data["data"], dict):
                        data = response_data["data"]
                        status = data.get("status", "")
                        video_url = data.get("video_url", "")
                        error_msg = data.get("error", None)
                        
                        return {
                            "status": "success",
                            "data": {
                                "status": status,
                                "video_url": video_url,
                                "error": error_msg,
                                "raw_data": data
                            }
                        }
                except Exception as e:
                    print(f"Error parsing primary response: {str(e)}")
        except Exception as e:
            print(f"Error with primary URL: {str(e)}")
        
        # If primary URL fails, try fallbacks with all header variants
        # Try all headers variants
        for i, headers in enumerate(self.headers_variants):
            # Only try the first 3 header variants for efficiency
            if i >= 3:
                break
                
            for url in fallback_urls:
                try:
                    print(f"Trying fallback URL: {url}")
                    print(f"Using headers: {headers}")
                    
                    response = requests.get(url, headers=headers, timeout=10)
                    
                    print(f"Response status code: {response.status_code}")
                    
                    # Try to parse response as JSON
                    try:
                        response_data = response.json()
                        print(f"Response data: {response_data}")
                        
                        # Extract status from response based on API version
                        status = None
                        video_url = None
                        error_msg = None
                        
                        # Check if it's v1 API response format
                        if isinstance(response_data, dict) and "data" in response_data:
                            data = response_data["data"]
                            
                            # v1 format directly contains status
                            if isinstance(data, dict) and "status" in data:
                                status = data["status"]
                            
                            # v1 format contains video_url directly 
                            if isinstance(data, dict) and "video_url" in data:
                                video_url = data["video_url"]
                            
                            # Error message
                            if isinstance(data, dict) and "err_msg" in data:
                                error_msg = data["err_msg"]
                        
                        # v2 API format might have a different structure
                        elif isinstance(response_data, dict) and "status" in response_data:
                            status = response_data["status"]
                            
                            # Check for video URL in v2 format
                            if "url" in response_data:
                                video_url = response_data["url"]
                            elif "video_url" in response_data:
                                video_url = response_data["video_url"]
                            
                            # Error message in v2 format
                            if "error" in response_data:
                                error_msg = response_data["error"]
                            elif "message" in response_data:
                                error_msg = response_data["message"]
                        
                        # Direct response format
                        elif isinstance(response_data, dict):
                            if "status" in response_data:
                                status = response_data["status"]
                            if "url" in response_data:
                                video_url = response_data["url"]
                            elif "video_url" in response_data:
                                video_url = response_data["video_url"]
                            if "error" in response_data:
                                error_msg = response_data["error"]
                        
                        if status:
                            # Store the working URL and headers for future requests
                            self.base_url = url.split('/videos')[0] if '/videos' in url else url.split('/video_status')[0]
                            self.headers = headers
                            
                            # Normalize status values
                            status = status.lower() if isinstance(status, str) else status
                            if status == "success":
                                status = "ready"
                            
                            return {
                                "status": "success",
                                "data": {
                                    "status": status,
                                    "video_url": video_url,
                                    "error": error_msg,
                                    "raw_data": response_data
                                }
                            }
                    except Exception as e:
                        print(f"Error parsing response: {str(e)}")
                        # If JSON parsing fails but response was successful, try to extract info from HTML
                        if response.status_code == 200:
                            try:
                                # Look for common patterns in response that might contain video URL
                                content = response.text
                                
                                # Try to find video URL using regex patterns
                                url_patterns = [
                                    r'https://[^\s"\']+\.mp4',  # Standard MP4 URL
                                    r'video_url["\']?\s*:\s*["\']?(https://[^\s"\']+)["\']?',  # JSON-like pattern
                                    r'url["\']?\s*:\s*["\']?(https://[^\s"\']+)["\']?'  # Another JSON-like pattern
                                ]
                                
                                for pattern in url_patterns:
                                    matches = re.findall(pattern, content)
                                    if matches:
                                        video_url = matches[0]
                                        print(f"Found video URL using pattern match: {video_url}")
                                        return {
                                            "status": "success",
                                            "data": {
                                                "status": "ready",  # Assume ready if URL found
                                                "video_url": video_url,
                                                "error": None,
                                                "raw_data": {"extracted_from_html": True}
                                            }
                                        }
                            except Exception as html_e:
                                print(f"Error extracting from HTML: {str(html_e)}")
                except Exception as e:
                    print(f"Error with {url}: {str(e)}")
        
        # If all endpoints fail, return the error
        return {
            "status": "error",
            "message": f"Failed to get video status for ID: {video_id}"
        }
    
    def wait_for_video_completion(self, video_id, max_wait_time=300, check_interval=5):
        """
        Wait for a video to complete processing
        
        Args:
            video_id: ID of the video to wait for
            max_wait_time: Maximum wait time in seconds
            check_interval: Time between status checks in seconds
            
        Returns:
            dict: Final status information
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            status_info = self.check_video_status(video_id)
            
            if status_info["status"] == "error":
                return status_info
            
            # Check various status formats based on API version
            video_status = status_info["data"].get("status", "")
            
            # Map different status terms to standard terms
            if video_status in ["ready", "completed", "done", "SUCCESS"]:
                return {
                    "status": "success",
                    "message": "Video generation completed",
                    "data": status_info["data"]
                }
            elif video_status in ["failed", "FAILURE", "error"]:
                return {
                    "status": "error",
                    "message": "Video generation failed",
                    "data": status_info["data"]
                }
            elif video_status in ["pending", "processing", "PROCESSING"]:
                print(f"Video still processing... ({int(time.time() - start_time)}s elapsed)")
            else:
                print(f"Unknown status: {video_status}")
            
            time.sleep(check_interval)
        
        return {
            "status": "error",
            "message": f"Timed out after waiting {max_wait_time} seconds"
        }
    
    def download_video(self, video_url, output_path):
        """
        Download a video from a URL
        
        Args:
            video_url: URL of the video to download
            output_path: Path where the video will be saved
            
        Returns:
            dict: Status information
        """
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            return {
                "status": "success",
                "message": f"Video downloaded to {output_path}",
                "file_path": output_path
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error downloading video: {str(e)}"
            }
    
    def estimate_duration(self, text):
        """Estimate duration in seconds based on text length"""
        words = len(text.split())
        # Average speaking rate is about 150 words per minute
        return max(1, math.ceil(words / 2.5))
    
    def generate_aroll(self, script, avatar_id=None, voice_id=None):
        """
        Generate an A-roll video with the given script
        
        Args:
            script: Text script for the video
            avatar_id: ID of the avatar to use (optional)
            voice_id: ID of the voice to use (optional)
            
        Returns:
            dict: Response with video information
        """
        # If script is too long (over 1500 chars), split it
        if len(script) > 1500:
            return self.split_and_generate_aroll(script, avatar_id, voice_id)
        
        # Create the talking video
        result = self.create_talking_video(script, avatar_id, voice_id)
        
        if result["status"] == "error":
            return result
        
        video_id = result["video_id"]
        
        # Wait for the video to be ready
        completion_result = self.wait_for_video_completion(video_id)
        
        if completion_result["status"] == "error":
            return completion_result
        
        # Get the video URL
        video_url = completion_result["data"].get("video_url", "")
        
        if not video_url:
            return {
                "status": "error",
                "message": "No video URL in the response"
            }
        
        # Create output directory if it doesn't exist
        output_dir = Path("media/a-roll")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Download the video
        output_path = output_dir / f"heygen_{video_id}.mp4"
        download_result = self.download_video(video_url, str(output_path))
        
        if download_result["status"] == "error":
            return download_result
        
        return {
            "status": "success",
            "message": "A-roll video generated successfully",
            "video_id": video_id,
            "file_path": str(output_path),
            "data": completion_result["data"]
        }
    
    def split_and_generate_aroll(self, script, avatar_id=None, voice_id=None):
        """
        Split a long script into segments and generate videos for each
        
        Args:
            script: Text script for the video
            avatar_id: ID of the avatar to use (optional)
            voice_id: ID of the voice to use (optional)
            
        Returns:
            dict: Response with video information
        """
        # Use default avatar and voice if not provided
        if not avatar_id:
            avatar_id = self.get_hardcoded_avatar_id()
        
        if not voice_id:
            voice_id = self.get_voice_id()
            
        print(f"Script too long ({len(script)} chars), splitting into segments")
        
        # Split the script into segments under 1500 characters
        segments = []
        
        # Try to split by sentences first for more natural breaks
        sentences = []
        sentence_pattern = r'([.!?])\s+'
        sentence_parts = re.split(sentence_pattern, script)
        
        current_sentence = ""
        for i in range(0, len(sentence_parts), 2):
            if i < len(sentence_parts):
                current_sentence += sentence_parts[i]
                if i+1 < len(sentence_parts):
                    current_sentence += sentence_parts[i+1]
                sentences.append(current_sentence)
                current_sentence = ""
        
        # Group sentences into segments under 1500 chars
        current_segment = ""
        for sentence in sentences:
            if len(current_segment) + len(sentence) <= 1500:
                current_segment += sentence
            else:
                if current_segment:
                    segments.append(current_segment)
                current_segment = sentence
        
        # Add the final segment if there's content left
        if current_segment:
            segments.append(current_segment)
        
        print(f"Split into {len(segments)} segments")
        
        # Generate video for each segment
        segment_results = []
        for i, segment_text in enumerate(segments):
            print(f"Generating segment {i+1}/{len(segments)}")
            result = self.create_talking_video(segment_text, avatar_id, voice_id)
            
            if result["status"] == "error":
                return {
                    "status": "error",
                    "message": f"Error generating segment {i+1}: {result['message']}"
                }
            
            video_id = result["video_id"]
            completion_result = self.wait_for_video_completion(video_id)
            
            if completion_result["status"] == "error":
                return {
                    "status": "error",
                    "message": f"Error while waiting for segment {i+1}: {completion_result['message']}"
                }
            
            video_url = completion_result["data"].get("video_url", "")
            
            if not video_url:
                return {
                    "status": "error",
                    "message": f"No video URL for segment {i+1}"
                }
            
            # Create output directory if it doesn't exist
            output_dir = Path("media/a-roll")
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Download the video
            output_path = output_dir / f"heygen_{video_id}_segment_{i}.mp4"
            download_result = self.download_video(video_url, str(output_path))
            
            if download_result["status"] == "error":
                return {
                    "status": "error",
                    "message": f"Error downloading segment {i+1}: {download_result['message']}"
                }
            
            segment_results.append({
                "segment": i,
                "video_id": video_id,
                "file_path": str(output_path)
            })
        
        # Return information about all segments
        return {
            "status": "success",
            "message": f"Generated {len(segments)} A-roll video segments successfully",
            "segments": segment_results,
            "file_paths": [r["file_path"] for r in segment_results]
        }

def test_heygen_api(api_key, test_text="Welcome to AI Money Printer Shorts!"):
    """
    Test the HeyGen API functionality
    
    Args:
        api_key: HeyGen API key (may be Base64 encoded)
        test_text: Text to use for the test video
        
    Returns:
        dict: Test results
    """
    try:
        # Initialize the API client
        client = HeyGenAPI(api_key)
        
        # Test connection
        print("Testing connection to HeyGen API...")
        connection_test = client.test_connection()
        
        # If connection test fails, return the error
        if connection_test["status"] == "error":
            return connection_test
            
        # If we got here, at least the connection works!
        print("Connection successful!")
        
        # List avatars
        print("Listing available avatars...")
        avatars_result = client.list_avatars()
        if avatars_result["status"] == "success":
            print(f"Found {len(avatars_result['data'])} avatars")
        else:
            print(f"Error listing avatars: {avatars_result['message']}")
            # Continue with default avatar
        
        # List voices
        print("Listing available voices...")
        voices_result = client.list_voices()
        if voices_result["status"] == "success":
            print(f"Found {len(voices_result['data'])} voices")
        else:
            print(f"Error listing voices: {voices_result['message']}")
            # Continue with default voice
        
        # Generate a test video only if requested with verbose flag
        
        # Return success
        return {
            "status": "success",
            "message": "HeyGen API connection test successful",
            "connection_test": connection_test,
            "avatars": avatars_result.get("data", []),
            "voices": voices_result.get("data", [])
        }
    
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error during HeyGen API test: {str(e)}"
        }

if __name__ == "__main__":
    # This allows running this script directly to test the API
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the HeyGen API")
    parser.add_argument("api_key", help="HeyGen API key")
    parser.add_argument("--text", help="Test text to use", default="Welcome to AI Money Printer Shorts!")
    parser.add_argument("--generate", help="Generate a test video", action="store_true")
    
    args = parser.parse_args()
    
    print("Testing HeyGen API...")
    result = test_heygen_api(args.api_key, args.text)
    
    if result["status"] == "success":
        print("✅ HeyGen API test successful")
        # Print connection details
        message = result.get("connection_test", {}).get("message", "Unknown")
        print(f"Connection details: {message}")
        
        # Generate a test video if requested
        if args.generate:
            client = HeyGenAPI(args.api_key)
            print("Generating test video...")
            video_result = client.generate_aroll(args.text)
            
            if video_result["status"] == "success":
                print(f"Test video generated successfully!")
                print(f"Video saved to: {video_result['file_path']}")
            else:
                print(f"Error generating test video: {video_result['message']}")
    else:
        print(f"❌ HeyGen API test failed: {result['message']}") 