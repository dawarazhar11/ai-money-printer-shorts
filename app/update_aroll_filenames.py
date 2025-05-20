#!/usr/bin/env python3
import json
import os
from pathlib import Path

# Current directory is assumed to be the app directory
app_dir = Path(os.getcwd())
aroll_dir = app_dir / "media" / "a-roll"

# Path to the content status JSON file
content_status_path = app_dir / "config" / "user_data" / "my_short_video" / "content_status.json"

# Define the mapping between segment IDs and full HeyGen IDs
id_mapping = {
    "segment_0": {"short_id": "5169ef5a", "full_id": "5169ef5a328149a8b13c365ee7060106"},
    "segment_1": {"short_id": "aed87db0", "full_id": "aed87db0234e4965825c7ee4c1067467"},
    "segment_2": {"short_id": "e7d47355", "full_id": "e7d47355c21e4190bad8752c799343ee"},
    "segment_3": {"short_id": "36064085", "full_id": "36064085e2a240768a8368bc6a911aea"}
}

# Load the content status data
with open(content_status_path, "r") as f:
    content_status = json.load(f)

# Check if we need to update the file paths
modified = False
for segment_id, mapping_info in id_mapping.items():
    if segment_id in content_status["aroll"]:
        # Get current file path
        current_path = content_status["aroll"][segment_id].get("file_path", "")
        
        # Update the prompt_id to the full ID
        content_status["aroll"][segment_id]["prompt_id"] = mapping_info["full_id"]
        
        # Update file paths to use the correct format with absolute paths
        heygen_file = f"heygen_{mapping_info['full_id']}.mp4"
        expected_file = f"fetched_aroll_segment_{segment_id[-1]}_{mapping_info['short_id']}.mp4"
        
        heygen_path = str(aroll_dir / heygen_file)
        expected_path = str(aroll_dir / expected_file)
        
        # Check which file exists and use that
        if os.path.exists(heygen_path):
            # If only the heygen file exists, make a copy with the expected name
            if not os.path.exists(expected_path):
                print(f"Creating copy: {heygen_file} -> {expected_file}")
                import shutil
                shutil.copy2(heygen_path, expected_path)
        
        # Update the file path to the absolute path of the expected file
        content_status["aroll"][segment_id]["file_path"] = expected_path
        print(f"Updated {segment_id} path: {expected_path}")
        modified = True

# Save the updated content status data
if modified:
    with open(content_status_path, "w") as f:
        json.dump(content_status, f, indent=4)
    print(f"Updated content status saved to: {content_status_path}")
else:
    print("No changes were made to content status.")

print("\nCurrent A-Roll files in media/a-roll directory:")
for file in aroll_dir.glob("*"):
    print(f" - {file.name}")
    
print("\nContent status A-Roll entries:")
for segment_id, data in content_status["aroll"].items():
    if segment_id.startswith("segment_"):
        print(f" - {segment_id}: {data.get('file_path', 'No path')}") 