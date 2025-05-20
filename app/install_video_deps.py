#!/usr/bin/env python3
"""
Direct installer for video processing dependencies
"""

import subprocess
import sys

print("Installing required packages for video assembly...")

# Install packages one by one with proper version specifiers
packages = [
    "moviepy==1.0.3",
    "numpy",
    "ffmpeg-python==0.2.0",
    "pillow"
]

for package in packages:
    print(f"Installing {package}...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", package
        ])
        print(f"✅ Successfully installed {package}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")

print("\nInstallation completed. Please check for any errors above.")
print("If you're still having issues, install these packages manually:")
print("  pip install moviepy==1.0.3 numpy ffmpeg-python==0.2.0 pillow")
print("\nMake sure ffmpeg is also installed on your system.") 