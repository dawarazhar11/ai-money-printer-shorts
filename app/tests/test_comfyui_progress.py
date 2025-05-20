import sys
import os
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.progress_tracker import ComfyUIProgressTracker

def test_websocket_connection():
    """Test websocket connection to ComfyUI"""
    print("Testing WebSocket connection to ComfyUI...")
    tracker = ComfyUIProgressTracker(ws_host="100.115.243.42", ws_port="8000")
    
    # Define callback function
    def callback(prompt_id, progress, status):
        if progress is not None:
            print(f"Progress: {progress:.2%}")
        if status:
            print(f"Status: {status}")
    
    # Test connection
    connected = tracker.connect()
    if connected:
        print("Connected to ComfyUI WebSocket server!")
        
        # You would need a valid prompt_id here
        # For testing, you can use a random string
        test_prompt_id = "test_prompt_id"
        
        print(f"Subscribing to prompt updates for: {test_prompt_id}")
        tracker.subscribe_to_prompt(test_prompt_id, callback)
        
        # Keep connection open for a bit to see if we get any messages
        try:
            print("Waiting for messages (press Ctrl+C to exit)...")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Test interrupted by user")
        finally:
            tracker.close()
    else:
        print("Failed to connect to ComfyUI WebSocket server")
        print("Ensure ComfyUI is running and WebSocket server is enabled")

if __name__ == "__main__":
    test_websocket_connection() 