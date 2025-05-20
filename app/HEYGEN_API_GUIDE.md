# HeyGen API Integration Guide for AI Money Printer Shorts

This guide explains how to use the improved HeyGen API integration for generating A-Roll videos in the AI Money Printer Shorts application.

## Features of the HeyGen API Integration

- Supports both HeyGen v1 and v2 API endpoints
- Automatic fallback between API versions if one fails
- Multiple authentication methods tried automatically
- Smart retry logic for avatar and voice IDs
- Support for splitting long scripts into segments and stitching them back together
- Detailed error reporting and logging
- Default avatars and voices that are known to work
- File browsing and preview capabilities
- Direct fetching of videos with specific segment IDs
- Downloading existing videos using their video IDs

## Testing the Integration

The simplest way to test the HeyGen API is to run the test script:

```bash
# With your API key as an argument
./test_heygen.py --api_key YOUR_API_KEY

# Or set the API key as an environment variable
export HEYGEN_API_KEY="YOUR_API_KEY"
./test_heygen.py

# Test connection only without generating a video
./test_heygen.py --test_only

# Specify custom text, avatar ID, or voice ID
./test_heygen.py --text "This is a test video" --avatar_id "Abigail_expressive_2024112501" --voice_id "119caed25533477ba63822d5d1552d25"

# Preview existing segment files
./test_heygen.py --preview

# Preview with detailed information
./test_heygen.py --preview --verbose

# Download existing videos from HeyGen by their IDs
./test_heygen.py --download --api_key YOUR_API_KEY
```

## Using in Your Code

Here's how to use the HeyGen API in your Python code:

```python
from utils.heygen_api import HeyGenAPI

# Initialize the client
api_key = "YOUR_API_KEY"
client = HeyGenAPI(api_key)

# Test connection (optional)
connection_test = client.test_connection()
if connection_test["status"] != "success":
    print(f"Connection failed: {connection_test['message']}")
    exit(1)

# Generate an A-roll video
script = "This is the script for your video. It can be quite long, as the API will automatically split it into segments if needed."
result = client.generate_aroll(script)

if result["status"] == "success":
    print(f"Video generated successfully!")
    print(f"Video saved to: {result['file_path']}")
    
    # If multiple segments were generated
    if "segments" in result:
        print(f"Generated {len(result['segments'])} segments")
        for segment in result["segments"]:
            print(f"Segment {segment['segment']}: {segment['file_path']}")
else:
    print(f"Error: {result['message']}")
```

## Default IDs

The integration comes with default IDs that are known to work with the HeyGen API:

### Default Avatar IDs
- `Abigail_expressive_2024112501` (Default avatar)
- `Adam_expressive_2024112501` (Alternative avatar)

### Default Voice IDs
- `119caed25533477ba63822d5d1552d25` (Arthur Blackwood, default voice)
- `9f8ff4eed26442168a8f2dc03c56e9ce` (Matt)
- `1582f2abbc114670b8999f22af70f09d` (Sarah)

You can use these IDs directly or let the API fetch available avatars and voices dynamically.

## Segment File Management

The integration now includes tools for managing segment files:

### Generating Test Files

You can create dummy segment files for testing:

```bash
# Create 5-second test videos
./create_dummy_segments.py

# Create custom duration test videos
./create_dummy_segments.py --duration 10
```

### Previewing Segment Files

You can preview information about existing segment files:

```bash
# Preview default segment files
./test_heygen.py --preview

# Show detailed information
./test_heygen.py --preview --verbose
```

### Downloading Existing HeyGen Videos

To download existing videos from HeyGen that have already been generated:

```bash
# Download existing videos using their IDs
./test_heygen.py --download --api_key YOUR_API_KEY

# Show more information during download
./test_heygen.py --download --api_key YOUR_API_KEY --verbose
```

The script will:
1. Check the status of each video in HeyGen
2. Download the video if it's ready
3. Save the file with the correct naming convention in the media/a-roll directory

This is useful when your videos have already been generated on HeyGen and you just need to fetch them into your application.

The test script is pre-configured with the following segment IDs:

- SEG1: `5169ef5a328149a8b13c365ee7060106`
- SEG2: `aed87db0234e4965825c7ee4c1067467`
- SEG3: `e7d47355c21e4190bad8752c799343ee`
- SEG4: `36064085e2a240768a8368bc6a911aea`

## Troubleshooting

If you encounter issues with the HeyGen API:

1. **404 Errors**: This usually indicates an incorrect API endpoint. The integration tries both v1 and v2 endpoints automatically.

2. **Authentication Errors**: The API key might be invalid. The integration tries different authentication methods (headers) automatically.

3. **Avatar/Voice Not Found**: The integration will fall back to default avatars and voices if the specified ones aren't found.

4. **Script Too Long**: Scripts over 1500 characters are automatically split into segments.

5. **File Not Found Errors**: If video files are not found, you can use the file preview feature to check what files exist and their paths.

6. **Video Not Ready**: When downloading existing videos, the "video not ready" status means the video is still processing on HeyGen's servers.

## API Endpoints

The integration supports these HeyGen API endpoints:

### v1 API Endpoints
- `/avatar.list` - List available avatars
- `/voice.list` - List available voices
- `/talking_photo` - Generate talking photo videos
- `/video_status.get` - Check video status
- `/talking_photo/{video_id}` - Check talking photo status

### v2 API Endpoints
- `/avatars` - List available avatars
- `/voices` - List available voices
- `/video/generate` - Generate videos
- `/videos/{video_id}` - Check video status

The integration automatically determines which endpoint to use based on what succeeds. 