import websocket
import threading
import json
import time
import requests
import streamlit as st
from datetime import datetime

# ComfyUI WebSocket Progress Tracking
class ComfyUIProgressTracker:
    def __init__(self, ws_host="100.115.243.42", ws_port="8000"):
        self.ws_url = f"ws://{ws_host}:{ws_port}/ws"
        self.ws = None
        self.callbacks = {}
        self.connected = False
        self.client_id = f"ai_money_printer_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
    def connect(self):
        """Connect to ComfyUI WebSocket server"""
        try:
            self.ws = websocket.WebSocketApp(
                self.ws_url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close
            )
            
            # Start WebSocket connection in a separate thread
            wst = threading.Thread(target=self.ws.run_forever)
            wst.daemon = True
            wst.start()
            
            # Wait for connection to establish
            timeout = 5
            start_time = time.time()
            while not self.connected and time.time() - start_time < timeout:
                time.sleep(0.1)
                
            return self.connected
        except Exception as e:
            print(f"WebSocket connection error: {e}")
            return False
    
    def _on_open(self, ws):
        """Handle WebSocket connection open"""
        self.connected = True
        # Send client ID to server
        self.ws.send(json.dumps({"client_id": self.client_id}))
    
    def _on_message(self, ws, message):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            prompt_id = data.get("data", {}).get("prompt_id")
            
            if prompt_id and prompt_id in self.callbacks:
                if msg_type == "progress":
                    # Progress update: value/max gives percentage
                    value = data["data"]["value"]
                    max_value = data["data"]["max"]
                    progress = value / max_value
                    self.callbacks[prompt_id](prompt_id, progress, "generating")
                
                elif msg_type == "executing":
                    # Node execution started
                    node = data["data"]["node"]
                    self.callbacks[prompt_id](prompt_id, None, f"processing node {node}")
                
                elif msg_type == "executed":
                    # Node execution completed
                    node = data["data"]["node"]
                    outputs = data["data"].get("output", {})
                    self.callbacks[prompt_id](prompt_id, None, f"completed node {node}")
                
                elif msg_type == "execution_error":
                    # Error during execution
                    error_msg = data["data"].get("exception_message", "Unknown error")
                    self.callbacks[prompt_id](prompt_id, None, f"error: {error_msg}")
                
                elif msg_type == "execution_complete":
                    # Generation completed
                    self.callbacks[prompt_id](prompt_id, 1.0, "complete")
        except Exception as e:
            print(f"Error processing WebSocket message: {e}")
    
    def _on_error(self, ws, error):
        """Handle WebSocket errors"""
        print(f"WebSocket error: {error}")
    
    def _on_close(self, ws, close_status_code, close_msg):
        """Handle WebSocket connection close"""
        self.connected = False
        print("WebSocket connection closed")
    
    def subscribe_to_prompt(self, prompt_id, callback):
        """Subscribe to updates for a specific prompt ID"""
        if not self.connected:
            success = self.connect()
            if not success:
                # Fallback to polling if WebSocket connection fails
                return False
        
        # Store callback for this prompt ID
        self.callbacks[prompt_id] = callback
        
        # Subscribe to prompt updates
        if self.ws and self.connected:
            self.ws.send(json.dumps({
                "op": "subscribe_to_prompt",
                "data": {"prompt_id": prompt_id}
            }))
            return True
        
        return False
    
    def close(self):
        """Close the WebSocket connection"""
        if self.ws:
            self.ws.close()

# Fallback polling for ComfyUI
def poll_comfyui_progress(api_url, prompt_id, callback, interval=1):
    """Poll ComfyUI API endpoints for progress updates"""
    running = True
    status_check_count = 0
    
    while running:
        try:
            # Check queue status (every other iteration to reduce load)
            if status_check_count % 2 == 0:
                queue_response = requests.get(f"{api_url}/queue", timeout=5)
                if queue_response.status_code == 200:
                    queue_data = queue_response.json()
                    
                    # Check if our job is in the running queue
                    is_running = False
                    for job in queue_data.get("queue_running", []):
                        if job.get("prompt_id") == prompt_id:
                            is_running = True
                            callback(prompt_id, 0.5, "running")
                    
                    # Check if job is pending
                    is_pending = False
                    for i, job in enumerate(queue_data.get("queue_pending", [])):
                        if job.get("prompt_id") == prompt_id:
                            is_pending = True
                            position = i + 1
                            callback(prompt_id, 0.1, f"pending (position {position} in queue)")
                    
                    # If not found in queue, check history
                    if not is_running and not is_pending:
                        history_check = True
            else:
                history_check = True
            
            # Check history to see if job completed
            if 'history_check' in locals() and history_check:
                history_response = requests.get(f"{api_url}/history/{prompt_id}", timeout=5)
                if history_response.status_code == 200:
                    # Endpoint returns object with prompt_id as key
                    data = history_response.json()
                    job_data = data.get(prompt_id, {})
                    status = job_data.get("status", {}).get("status", "unknown")
                    
                    if status == "success":
                        callback(prompt_id, 1.0, "complete")
                        running = False
                    elif status == "error":
                        error_msg = job_data.get("status", {}).get("error", "Unknown error")
                        callback(prompt_id, None, f"error: {error_msg}")
                        running = False
            
            status_check_count += 1
            time.sleep(interval)
        except Exception as e:
            print(f"Error polling progress: {e}")
            time.sleep(interval * 2)  # Back off on errors

# Replicate API Progress Tracking
def track_replicate_progress(prediction_id, api_token, callback, interval=2):
    """Track progress of Replicate API generation"""
    headers = {
        "Authorization": f"Token {api_token}",
        "Content-Type": "application/json"
    }
    
    running = True
    while running:
        try:
            response = requests.get(
                f"https://api.replicate.com/v1/predictions/{prediction_id}",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get("status")
                
                if status == "starting":
                    callback(prediction_id, 0.1, "starting")
                elif status == "processing":
                    # Replicate sometimes provides progress in logs
                    logs = data.get("logs", "")
                    progress = extract_progress_from_logs(logs) 
                    callback(prediction_id, progress or 0.5, "processing")
                elif status == "succeeded":
                    callback(prediction_id, 1.0, "complete")
                    running = False
                elif status in ["failed", "canceled"]:
                    error = data.get("error")
                    callback(prediction_id, 0, f"error: {error}")
                    running = False
            else:
                # Handle API errors
                callback(prediction_id, None, f"API error: {response.status_code}")
                time.sleep(interval * 2)
            
            time.sleep(interval)
        except Exception as e:
            print(f"Error tracking Replicate progress: {e}")
            time.sleep(interval * 2)

def extract_progress_from_logs(logs):
    """Extract progress percentage from Replicate logs"""
    if not logs:
        return None
        
    import re
    progress_matches = re.findall(r"(\d+)%", logs)
    if progress_matches:
        # Return the last percentage found, divided by 100
        return float(progress_matches[-1]) / 100
    return None

# Streamlit integration
def setup_progress_tracking_ui(job_type, job_id, api_url=None, api_token=None):
    """Create Streamlit progress tracking UI elements"""
    container = st.container()
    
    with container:
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initial status
        status_text.info(f"Starting {job_type} generation...")
    
    def update_progress(id, progress, status=None):
        if id == job_id:
            if progress is not None:
                # Ensure progress is within [0,1] range
                safe_progress = max(0.0, min(1.0, float(progress)))
                progress_bar.progress(safe_progress)
            
            if status:
                if status == "complete":
                    status_text.success(f"{job_type} generation complete!")
                elif status.startswith("error"):
                    status_text.error(status)
                else:
                    status_text.info(f"Status: {status}")
    
    return update_progress, container

# Initialize trackers as needed
def start_comfyui_tracking(prompt_id, api_url):
    """Start tracking ComfyUI generation progress"""
    update_callback, container = setup_progress_tracking_ui("ComfyUI", prompt_id)
    
    # Try WebSocket connection first (preferred method)
    tracker = ComfyUIProgressTracker()
    success = tracker.subscribe_to_prompt(prompt_id, update_callback)
    
    # Fall back to polling if WebSocket fails
    if not success:
        with container:
            st.caption("Using fallback polling method for progress updates")
        
        # Start polling in background thread
        thread = threading.Thread(
            target=lambda: poll_comfyui_progress(api_url, prompt_id, update_callback)
        )
        thread.daemon = True
        thread.start()
    
    return tracker  # Return tracker so it can be closed later

def start_replicate_tracking(prediction_id, api_token):
    """Start tracking Replicate generation progress"""
    update_callback, _ = setup_progress_tracking_ui("Replicate", prediction_id)
    
    # Start tracking in background thread
    thread = threading.Thread(
        target=lambda: track_replicate_progress(prediction_id, api_token, update_callback)
    )
    thread.daemon = True
    thread.start()
    
    return thread  # Return thread for reference 