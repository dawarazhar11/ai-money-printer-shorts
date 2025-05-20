#!/usr/bin/env python3
import json
import os
from pathlib import Path

# Current directory is assumed to be the app directory
app_dir = Path(os.getcwd())
aroll_dir = app_dir / "media" / "a-roll"

# Path to the content status JSON file
content_status_path = app_dir / "config" / "user_data" / "my_short_video" / "content_status.json"

# Load the content status data
with open(content_status_path, "r") as f:
    content_status = json.load(f)

# Update A-Roll paths to absolute paths
modified = False
for segment_id, segment_data in content_status["aroll"].items():
    if segment_id.startswith("segment_") and "file_path" in segment_data:
        filename = segment_data["file_path"]
        if not os.path.isabs(filename):
            # Convert to absolute path
            absolute_path = str(aroll_dir / filename)
            
            # Check if the file exists before updating
            if os.path.exists(absolute_path):
                segment_data["file_path"] = absolute_path
                print(f"Updated path for {segment_id}: {absolute_path}")
                modified = True
            else:
                print(f"Warning: File not found: {absolute_path}")

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