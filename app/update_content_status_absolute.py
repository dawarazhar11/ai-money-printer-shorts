#!/usr/bin/env python3
import json
import os
from pathlib import Path

# Current directory is assumed to be the app directory
app_dir = Path(os.getcwd())
aroll_dir = app_dir / "media" / "a-roll"
broll_dir = app_dir / "config" / "user_data" / "my_short_video" / "media" / "broll"

# Path to the content status JSON file
content_status_path = app_dir / "config" / "user_data" / "my_short_video" / "content_status.json"

# Load the content status data
with open(content_status_path, "r") as f:
    content_status = json.load(f)

# Define the mapping between segment IDs and full HeyGen IDs
id_mapping = {
    "segment_0": {"short_id": "5169ef5a", "full_id": "5169ef5a328149a8b13c365ee7060106"},
    "segment_1": {"short_id": "aed87db0", "full_id": "aed87db0234e4965825c7ee4c1067467"},
    "segment_2": {"short_id": "e7d47355", "full_id": "e7d47355c21e4190bad8752c799343ee"},
    "segment_3": {"short_id": "36064085", "full_id": "36064085e2a240768a8368bc6a911aea"}
}

# Update A-Roll paths to absolute paths
modified = False
for segment_id, mapping_info in id_mapping.items():
    if segment_id in content_status["aroll"]:
        # Update the prompt_id to the full ID
        content_status["aroll"][segment_id]["prompt_id"] = mapping_info["full_id"]
        
        # Define the expected filenames
        expected_file = f"fetched_aroll_segment_{segment_id[-1]}_{mapping_info['short_id']}.mp4"
        heygen_file = f"heygen_{mapping_info['full_id']}.mp4"
        
        expected_path = str(aroll_dir / expected_file)
        heygen_path = str(aroll_dir / heygen_file)
        
        # Check if either file exists
        if os.path.exists(expected_path):
            content_status["aroll"][segment_id]["file_path"] = expected_path
            print(f"Updated {segment_id} path to: {expected_path}")
            modified = True
        elif os.path.exists(heygen_path):
            # Make a copy with the expected filename if it doesn't exist
            if not os.path.exists(expected_path):
                import shutil
                shutil.copy2(heygen_path, expected_path)
                print(f"Created copy: {heygen_file} -> {expected_file}")
            
            content_status["aroll"][segment_id]["file_path"] = expected_path
            print(f"Updated {segment_id} path to: {expected_path}")
            modified = True
        else:
            print(f"Warning: No file found for {segment_id}")

# Update B-Roll paths to absolute paths
for segment_id, segment_data in content_status["broll"].items():
    if segment_id.startswith("segment_") and "file_path" in segment_data:
        file_path = segment_data["file_path"]
        
        # Don't modify already absolute paths
        if os.path.isabs(file_path):
            continue
            
        # For B-Roll files in the project directory
        if file_path.startswith("config/"):
            absolute_path = str(app_dir / file_path)
            if os.path.exists(absolute_path):
                segment_data["file_path"] = absolute_path
                print(f"Updated B-Roll {segment_id} path to absolute: {absolute_path}")
                modified = True

# Remove any extra segments that aren't needed
if "segment" in content_status["aroll"]:
    del content_status["aroll"]["segment"]
    modified = True
    print("Removed extra 'segment' entry from A-Roll")
    
if "segment" in content_status["broll"]:
    del content_status["broll"]["segment"]
    modified = True
    print("Removed extra 'segment' entry from B-Roll")

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

print("\nCurrent content status A-Roll entries:")
for segment_id, data in content_status["aroll"].items():
    if segment_id.startswith("segment_"):
        file_exists = os.path.exists(data.get("file_path", ""))
        print(f" - {segment_id}: {data.get('file_path', 'No path')} {'(EXISTS)' if file_exists else '(MISSING)'}")

print("\nCurrent content status B-Roll entries:")
for segment_id, data in content_status["broll"].items():
    if segment_id.startswith("segment_"):
        file_exists = os.path.exists(data.get("file_path", ""))
        print(f" - {segment_id}: {data.get('file_path', 'No path')} {'(EXISTS)' if file_exists else '(MISSING)'}") 