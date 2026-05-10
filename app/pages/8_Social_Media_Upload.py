#!/usr/bin/env python3
"""
Page for uploading videos to social media platforms (YouTube, TikTok, Instagram)
"""
import os
import sys
import json
import time
import traceback
from pathlib import Path
import streamlit as st
import requests
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Add the parent directory to sys.path
app_dir = Path(__file__).parent.parent.absolute()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
    print(f"Added {app_dir} to path")

try:
    from components.progress import render_step_header
    from utils.session_state import mark_step_complete
    from components.navigation import render_workflow_navigation, render_step_navigation
    print("Successfully imported local modules")
except ImportError as e:
    st.error(f"Error importing modules: {e}")
    st.info("Please make sure you're running this from the project root directory.")
    st.stop()

# Set page config
st.set_page_config(
    page_title="Publishing | ReelForge",
    page_icon="🚀",
    layout="wide"
)

# Initialize session state for this page
if "social_media_upload" not in st.session_state:
    st.session_state.social_media_upload = {
        "status": "not_started",
        "source_video": None,
        "youtube_status": "not_started",
        "tiktok_status": "not_started",
        "instagram_status": "not_started",
        "youtube_credentials": None,
        "tiktok_credentials": None,
        "instagram_credentials": None,
        "youtube_video_id": None,
        "tiktok_video_id": None,
        "instagram_video_id": None,
        "error": None
    }

# YouTube API scope
YOUTUBE_SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
YOUTUBE_API_SERVICE_NAME = 'youtube'
YOUTUBE_API_VERSION = 'v3'
YOUTUBE_CLIENT_SECRETS_FILE = 'client_secret.json'

# TikTok API details (these would need to be filled in with actual values)
TIKTOK_API_URL = 'https://open.tiktokapis.com/v2/video/upload/'

# Instagram API details (these would need to be filled in with actual values)
INSTAGRAM_API_URL = 'https://graph.instagram.com/me/media'

def authenticate_youtube():
    """Authenticate with YouTube API and return credentials"""
    try:
        # Check if client secrets file exists
        if not os.path.exists(YOUTUBE_CLIENT_SECRETS_FILE):
            return {
                "status": "error",
                "message": f"YouTube client secrets file not found: {YOUTUBE_CLIENT_SECRETS_FILE}"
            }
        
        # Create flow instance
        flow = InstalledAppFlow.from_client_secrets_file(
            YOUTUBE_CLIENT_SECRETS_FILE, YOUTUBE_SCOPES)
        
        # Run local server flow
        credentials = flow.run_local_server(port=8080)
        
        return {
            "status": "success",
            "credentials": credentials
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"YouTube authentication error: {str(e)}",
            "traceback": traceback.format_exc()
        }

def upload_to_youtube(video_path, title, description, tags, category_id="22", privacy_status="public", credentials=None):
    """
    Upload a video to YouTube
    
    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description
        tags: List of tags
        category_id: YouTube category ID (22 = People & Blogs)
        privacy_status: Privacy status (public, unlisted, private)
        credentials: YouTube API credentials
        
    Returns:
        dict: Upload status and video ID if successful
    """
    try:
        # Check if video exists
        if not os.path.exists(video_path):
            return {
                "status": "error",
                "message": f"Video file not found: {video_path}"
            }
        
        # Get or authenticate YouTube credentials
        if credentials is None:
            auth_result = authenticate_youtube()
            if auth_result["status"] != "success":
                return auth_result
            credentials = auth_result["credentials"]
        
        # Build YouTube API client
        youtube = build(YOUTUBE_API_SERVICE_NAME, YOUTUBE_API_VERSION, credentials=credentials)
        
        # Set up video metadata
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': category_id
            },
            'status': {
                'privacyStatus': privacy_status
            }
        }
        
        # Set up media file
        media = MediaFileUpload(
            video_path,
            mimetype='video/mp4',
            resumable=True
        )
        
        # Execute upload request
        upload_request = youtube.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )
        
        # Upload the video and show progress
        response = None
        while response is None:
            status, response = upload_request.next_chunk()
            if status:
                st.progress(int(status.progress() * 100))
                
        # Get the video ID
        video_id = response['id']
        
        return {
            "status": "success",
            "video_id": video_id,
            "url": f"https://www.youtube.com/watch?v={video_id}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"YouTube upload error: {str(e)}",
            "traceback": traceback.format_exc()
        }

def upload_to_tiktok(video_path, title, description):
    """
    Upload a video to TikTok
    
    Args:
        video_path: Path to the video file
        title: Video title
        description: Video description
        
    Returns:
        dict: Upload status and video ID if successful
    """
    try:
        # This is a placeholder for TikTok API integration
        # Actual implementation would require TikTok API credentials and SDK
        st.warning("TikTok API integration is not yet fully implemented")
        
        # Mock successful upload for demonstration
        return {
            "status": "success",
            "video_id": "tiktok_mock_id_12345",
            "message": "TikTok upload functionality is a placeholder. Implementation requires TikTok API access."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"TikTok upload error: {str(e)}",
            "traceback": traceback.format_exc()
        }

def upload_to_instagram(video_path, caption):
    """
    Upload a video to Instagram
    
    Args:
        video_path: Path to the video file
        caption: Video caption
        
    Returns:
        dict: Upload status and media ID if successful
    """
    try:
        # This is a placeholder for Instagram API integration
        # Actual implementation would require Instagram API credentials and SDK
        st.warning("Instagram API integration is not yet fully implemented")
        
        # Mock successful upload for demonstration
        return {
            "status": "success",
            "video_id": "instagram_mock_id_12345",
            "message": "Instagram upload functionality is a placeholder. Implementation requires Instagram API access."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Instagram upload error: {str(e)}",
            "traceback": traceback.format_exc()
        }

def main():
    """Main function for the Social Media Upload page"""
    # Header and navigation
    render_step_header("Social Media Upload", "Upload your captioned video to YouTube, TikTok, and Instagram")
    render_workflow_navigation()
    
    # Introduction
    st.markdown("""
    # 🚀 Social Media Upload
    
    Upload your captioned video to social media platforms to reach your audience!
    
    This page allows you to automatically publish your video to:
    - YouTube
    - TikTok
    - Instagram
    
    Configure your upload settings and publish with a single click.
    """)
    
    # Display the video selection panel
    st.markdown("## Step 1: Select the Video")
    
    # Option to use the previously captioned video or upload a custom one
    video_source = st.radio(
        "Video Source:",
        ["Use Captioned Video", "Upload Custom Video"],
        key="video_source"
    )
    
    if video_source == "Use Captioned Video":
        # Check for captioned video from previous step
        if "caption_dreams" in st.session_state and st.session_state.caption_dreams.get("output_path"):
            captioned_video_path = st.session_state.caption_dreams["output_path"]
            if os.path.exists(captioned_video_path):
                st.session_state.social_media_upload["source_video"] = captioned_video_path
                st.success(f"Using captioned video: {os.path.basename(captioned_video_path)}")
                
                # Display the video
                st.video(captioned_video_path)
            else:
                st.error("The captioned video file no longer exists. Please choose another option.")
                st.session_state.social_media_upload["source_video"] = None
        else:
            st.warning("No captioned video found. Please go to the Caption The Dreams page first or upload a custom video.")
            st.session_state.social_media_upload["source_video"] = None
    else:
        # Upload custom video
        uploaded_file = st.file_uploader("Upload your video file:", type=["mp4", "mov", "avi", "mkv"])
        if uploaded_file:
            # Save the uploaded file to a temporary location
            os.makedirs("output", exist_ok=True)
            temp_path = os.path.join("output", f"uploaded_{int(time.time())}.mp4")
            
            try:
                with open(temp_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                # Verify the file was written successfully
                if os.path.exists(temp_path) and os.path.getsize(temp_path) > 0:
                    st.session_state.social_media_upload["source_video"] = temp_path
                    st.success(f"Video uploaded successfully: {os.path.basename(temp_path)}")
                    
                    # Display the video
                    st.video(temp_path)
                else:
                    st.error("Failed to save uploaded video. The file may be empty or corrupted.")
            except Exception as e:
                st.error(f"Error saving uploaded video: {str(e)}")
                st.session_state.social_media_upload["source_video"] = None
    
    # Configure upload settings
    if st.session_state.social_media_upload["source_video"]:
        st.markdown("## Step 2: Configure Upload Settings")
        
        # Common metadata
        st.subheader("Video Metadata")
        
        title = st.text_input(
            "Video Title:",
            value="My AI-Generated Short Video",
            help="Enter a catchy title for your video"
        )
        
        description = st.text_area(
            "Description:",
            value="Created with ReelForge.\n\n#AIVideo #Shorts #ContentCreation",
            help="Enter a description for your video"
        )
        
        tags = st.text_input(
            "Tags (comma separated):",
            value="AIVideo, Shorts, ContentCreation",
            help="Enter tags separated by commas"
        ).split(",")
        tags = [tag.strip() for tag in tags if tag.strip()]
        
        # Platform-specific settings
        st.markdown("## Step 3: Choose Platforms to Upload")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            youtube_upload = st.checkbox("Upload to YouTube", value=True)
            if youtube_upload:
                youtube_category = st.selectbox(
                    "YouTube Category:",
                    [
                        "Film & Animation",
                        "Autos & Vehicles",
                        "Music",
                        "Pets & Animals",
                        "Sports",
                        "Travel & Events",
                        "Gaming",
                        "People & Blogs",
                        "Comedy",
                        "Entertainment",
                        "News & Politics",
                        "Howto & Style",
                        "Education",
                        "Science & Technology",
                        "Nonprofits & Activism"
                    ],
                    index=7  # People & Blogs
                )
                
                # Map category names to IDs
                category_map = {
                    "Film & Animation": "1",
                    "Autos & Vehicles": "2",
                    "Music": "10",
                    "Pets & Animals": "15",
                    "Sports": "17",
                    "Travel & Events": "19",
                    "Gaming": "20",
                    "People & Blogs": "22",
                    "Comedy": "23",
                    "Entertainment": "24",
                    "News & Politics": "25",
                    "Howto & Style": "26",
                    "Education": "27",
                    "Science & Technology": "28",
                    "Nonprofits & Activism": "29"
                }
                
                youtube_privacy = st.selectbox(
                    "Privacy Setting:",
                    ["public", "unlisted", "private"],
                    index=1  # unlisted
                )
        
        with col2:
            tiktok_upload = st.checkbox("Upload to TikTok", value=False)
            if tiktok_upload:
                st.info("TikTok API integration requires developer access. This is currently a placeholder.")
                
                tiktok_auth_status = st.empty()
                if st.button("Connect TikTok Account"):
                    with st.spinner("Connecting to TikTok..."):
                        # This would be replaced with actual TikTok authentication
                        time.sleep(2)
                        tiktok_auth_status.warning("TikTok API integration is not yet implemented")
        
        with col3:
            instagram_upload = st.checkbox("Upload to Instagram", value=False)
            if instagram_upload:
                st.info("Instagram API integration requires developer access. This is currently a placeholder.")
                
                instagram_auth_status = st.empty()
                if st.button("Connect Instagram Account"):
                    with st.spinner("Connecting to Instagram..."):
                        # This would be replaced with actual Instagram authentication
                        time.sleep(2)
                        instagram_auth_status.warning("Instagram API integration is not yet implemented")
        
        # Upload button
        st.markdown("## Step 4: Upload Video")
        
        if not (youtube_upload or tiktok_upload or instagram_upload):
            st.warning("Please select at least one platform to upload to.")
        else:
            if st.button("🚀 Upload Video", key="upload_btn", use_container_width=True):
                with st.spinner("Preparing to upload..."):
                    video_path = st.session_state.social_media_upload["source_video"]
                    
                    # Create containers for platform results
                    youtube_result = st.empty()
                    tiktok_result = st.empty()
                    instagram_result = st.empty()
                    
                    # Upload to YouTube
                    if youtube_upload:
                        youtube_result.info("Uploading to YouTube...")
                        youtube_category_id = category_map.get(youtube_category, "22")
                        
                        result = upload_to_youtube(
                            video_path=video_path,
                            title=title,
                            description=description,
                            tags=tags,
                            category_id=youtube_category_id,
                            privacy_status=youtube_privacy
                        )
                        
                        if result["status"] == "success":
                            st.session_state.social_media_upload["youtube_status"] = "completed"
                            st.session_state.social_media_upload["youtube_video_id"] = result["video_id"]
                            youtube_result.success(f"✅ Uploaded to YouTube: {result['url']}")
                        else:
                            st.session_state.social_media_upload["youtube_status"] = "error"
                            st.session_state.social_media_upload["error"] = result.get("message")
                            youtube_result.error(f"❌ YouTube upload failed: {result.get('message')}")
                            
                            # Show detailed error
                            if "traceback" in result:
                                with st.expander("YouTube Error Details"):
                                    st.code(result["traceback"])
                    
                    # Upload to TikTok
                    if tiktok_upload:
                        tiktok_result.info("Uploading to TikTok...")
                        time.sleep(2)  # Simulated upload time
                        
                        result = upload_to_tiktok(
                            video_path=video_path,
                            title=title,
                            description=description
                        )
                        
                        if result["status"] == "success":
                            st.session_state.social_media_upload["tiktok_status"] = "completed"
                            st.session_state.social_media_upload["tiktok_video_id"] = result["video_id"]
                            tiktok_result.warning(f"⚠️ TikTok upload (placeholder): {result.get('message')}")
                        else:
                            st.session_state.social_media_upload["tiktok_status"] = "error"
                            st.session_state.social_media_upload["error"] = result.get("message")
                            tiktok_result.error(f"❌ TikTok upload failed: {result.get('message')}")
                    
                    # Upload to Instagram
                    if instagram_upload:
                        instagram_result.info("Uploading to Instagram...")
                        time.sleep(2)  # Simulated upload time
                        
                        result = upload_to_instagram(
                            video_path=video_path,
                            caption=f"{title}\n\n{description}"
                        )
                        
                        if result["status"] == "success":
                            st.session_state.social_media_upload["instagram_status"] = "completed"
                            st.session_state.social_media_upload["instagram_video_id"] = result["video_id"]
                            instagram_result.warning(f"⚠️ Instagram upload (placeholder): {result.get('message')}")
                        else:
                            st.session_state.social_media_upload["instagram_status"] = "error"
                            st.session_state.social_media_upload["error"] = result.get("message")
                            instagram_result.error(f"❌ Instagram upload failed: {result.get('message')}")
                    
                    # Check if any uploads were successful
                    if (st.session_state.social_media_upload["youtube_status"] == "completed" or
                        st.session_state.social_media_upload["tiktok_status"] == "completed" or
                        st.session_state.social_media_upload["instagram_status"] == "completed"):
                        
                        st.session_state.social_media_upload["status"] = "completed"
                        mark_step_complete("social_media_upload")
                        
                        st.success("🎉 Video upload process completed!")
                    else:
                        st.session_state.social_media_upload["status"] = "error"
                        st.error("❌ All uploads failed. Please check the error messages above.")

# Run the main function
if __name__ == "__main__":
    main()
