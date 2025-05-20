#!/usr/bin/env python3
"""
Default B-Roll IDs and integration with video assembly
"""

import os
from pathlib import Path

# Default B-Roll segment IDs
DEFAULT_BROLL_IDS = [
    "ca26f439-3be6-4897-9e8a-d56448f4bb9a",
    "15027251-6c76-4aee-b5d1-adddfa591257",
    "8f34773a-a113-494b-be8a-e5ecd241a8a4"
]

def get_default_broll_id(index):
    """Get the default B-Roll ID for a given index"""
    if 0 <= index < len(DEFAULT_BROLL_IDS):
        return DEFAULT_BROLL_IDS[index]
    return None

def apply_default_broll_ids(content_status):
    """
    Apply default B-Roll IDs to the content status
    
    Args:
        content_status: Content status dictionary to modify
        
    Returns:
        bool: True if any changes were made, False otherwise
    """
    modified = False
    
    # Make sure the B-Roll section exists
    if "broll" not in content_status:
        content_status["broll"] = {}
    
    # Apply default IDs to each B-Roll segment
    for i, broll_id in enumerate(DEFAULT_BROLL_IDS):
        segment_id = f"segment_{i}"
        
        # Create or update the segment
        if segment_id not in content_status["broll"]:
            content_status["broll"][segment_id] = {}
            
        # Update the prompt_id
        if "prompt_id" not in content_status["broll"][segment_id] or content_status["broll"][segment_id]["prompt_id"] != broll_id:
            content_status["broll"][segment_id]["prompt_id"] = broll_id
            content_status["broll"][segment_id]["status"] = "assigned"  # Mark as assigned but not yet processed
            modified = True
            print(f"Applied default B-Roll ID for {segment_id}: {broll_id}")
    
    return modified

def update_session_state_with_defaults(session_state):
    """
    Update session state with default B-Roll IDs
    
    Args:
        session_state: Streamlit session state to modify
        
    Returns:
        bool: True if any changes were made, False otherwise
    """
    modified = False
    
    # Initialize broll_fetch_ids if it doesn't exist
    if "broll_fetch_ids" not in session_state:
        session_state.broll_fetch_ids = {}
    
    # Apply default IDs to broll_fetch_ids
    for i, broll_id in enumerate(DEFAULT_BROLL_IDS):
        segment_id = f"segment_{i}"
        
        # Update fetch IDs
        if segment_id not in session_state.broll_fetch_ids or session_state.broll_fetch_ids[segment_id] != broll_id:
            session_state.broll_fetch_ids[segment_id] = broll_id
            modified = True
            print(f"Updated session state B-Roll ID for {segment_id}: {broll_id}")
    
    return modified 