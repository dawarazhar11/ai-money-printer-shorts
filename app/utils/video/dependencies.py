#!/usr/bin/env python3
"""
Check and install dependencies for video processing
"""

import os
import sys
import subprocess
import importlib.util

# List of required packages with versions
REQUIRED_PACKAGES = [
    ("moviepy", "1.0.3"),
    ("numpy", None),  # Let pip decide version
    ("ffmpeg-python", "0.2.0"),  # Added for direct ffmpeg access
    ("pillow", None)  # For image processing
]

def check_package(package_name, required_version=None):
    """Check if a package is installed and get its version"""
    try:
        spec = importlib.util.find_spec(package_name)
        if spec is None:
            print(f"❌ {package_name} is not installed")
            return False

        if required_version:
            # Try to get the installed version
            try:
                package = importlib.import_module(package_name)
                installed_version = getattr(package, "__version__", "unknown")
                print(f"✅ {package_name} is installed (version: {installed_version})")
                return True
            except ImportError:
                print(f"✅ {package_name} is installed but couldn't determine version")
                return True
        else:
            print(f"✅ {package_name} is installed")
            return True
    except Exception as e:
        print(f"❌ Error checking {package_name}: {str(e)}")
        return False

def check_ffmpeg():
    """Check if ffmpeg is available"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode == 0:
            version_line = result.stdout.strip().split('\n')[0]
            print(f"✅ ffmpeg is installed: {version_line}")
            return True
        else:
            print("❌ ffmpeg is installed but not working correctly")
            return False
    except FileNotFoundError:
        print("❌ ffmpeg not found. Please install ffmpeg.")
        return False

def install_packages():
    """Install all required packages"""
    for package, version in REQUIRED_PACKAGES:
        package_spec = f"{package}{f'=={version}' if version else ''}"
        
        try:
            subprocess.check_call([
                sys.executable, "-m", "pip", "install", package_spec
            ])
            print(f"✅ Successfully installed {package_spec}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install {package_spec}: {str(e)}")

def main():
    print("Checking dependencies for video processing...")
    
    # Check installed packages
    missing_packages = []
    for package, version in REQUIRED_PACKAGES:
        if not check_package(package, version):
            missing_packages.append((package, version))
    
    # Check ffmpeg
    ffmpeg_available = check_ffmpeg()
    
    if missing_packages:
        print("\nMissing packages:")
        for package, version in missing_packages:
            print(f"  - {package}" + (f" (version {version})" if version else ""))
        
        # Ask to install
        install = input("\nDo you want to install missing packages? (y/n): ").lower() == 'y'
        if install:
            install_packages()
    
    if not ffmpeg_available:
        print("\nFFmpeg is required for video processing.")
        print("Please install FFmpeg using your system's package manager:")
        print("  - On macOS: brew install ffmpeg")
        print("  - On Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("  - On Windows: Download from https://ffmpeg.org/download.html")
    
    if not missing_packages and ffmpeg_available:
        print("\n✅ All dependencies are installed!")
        return 0
    else:
        print("\n❌ Some dependencies are missing.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 