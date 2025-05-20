#!/usr/bin/env python3
import os
import sys
import requests
import json
from pathlib import Path

def test_heygen_status():
    """
    Test the exact HeyGen API endpoint for retrieving video status as specified in documentation
    """
    # Use the API key that worked
    api_key = "Y2UyMGY2NTZmZTNjNDhiYjk1MjhjZDUwNzlkMWJjMTEtMTc0NzcyMTE2OA=="
    
    # Test each segment ID with the exact endpoint format from documentation
    segment_ids = [
        "5169ef5a328149a8b13c365ee7060106",
        "aed87db0234e4965825c7ee4c1067467", 
        "e7d47355c21e4190bad8752c799343ee",
        "36064085e2a240768a8368bc6a911aea"
    ]
    
    headers = {
        "accept": "application/json",
        "x-api-key": api_key
    }
    
    for video_id in segment_ids:
        # Use the exact endpoint specified in documentation
        url = f"https://api.heygen.com/v1/video_status.get?video_id={video_id}"
        
        print(f"\nChecking video status for ID: {video_id}")
        print(f"URL: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Response data: {json.dumps(data, indent=2)}")
                
                # Extract key information
                if "video_url" in data:
                    print(f"Video URL: {data['video_url']}")
                elif "data" in data and "video_url" in data["data"]:
                    print(f"Video URL: {data['data']['video_url']}")
                
                if "status" in data:
                    print(f"Status: {data['status']}")
                elif "data" in data and "status" in data["data"]:
                    print(f"Status: {data['data']['status']}")
            else:
                print(f"Error response: {response.text}")
        except Exception as e:
            print(f"Exception: {str(e)}")

if __name__ == "__main__":
    test_heygen_status() 