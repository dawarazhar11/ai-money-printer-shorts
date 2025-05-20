#!/usr/bin/env python3
"""
Dependency installer for video processing and captioning
"""

import os
import sys
import subprocess
import platform

def check_pip():
    """Check if pip is available and up to date"""
    try:
        import pip
        return True
    except ImportError:
        print("❌ pip is not installed. Please install pip first.")
        return False

def check_command(command):
    """Check if a command is available"""
    try:
        subprocess.run([command, "--version"], 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE)
        return True
    except:
        return False

def install_package(package, version=None):
    """Install a Python package using pip"""
    try:
        package_spec = f"{package}=={version}" if version else package
        print(f"Installing {package_spec}...")
        subprocess.run([sys.executable, "-m", "pip", "install", package_spec], 
                      check=True)
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {str(e)}")
        return False

def check_ffmpeg():
    """Check if ffmpeg is installed and print installation instructions if not"""
    if check_command("ffmpeg"):
        result = subprocess.run(["ffmpeg", "-version"], 
                               stdout=subprocess.PIPE, 
                               stderr=subprocess.PIPE, 
                               text=True)
        print(f"✅ ffmpeg is installed: {result.stdout.split('\\n')[0]}")
        return True
    else:
        print("❌ ffmpeg is not installed.")
        system = platform.system().lower()
        if system == "darwin":
            print("To install ffmpeg on macOS, use Homebrew:")
            print("  brew install ffmpeg")
        elif system == "windows":
            print("To install ffmpeg on Windows:")
            print("  1. Download from https://ffmpeg.org/download.html")
            print("  2. Or use Chocolatey: choco install ffmpeg")
        else:  # Linux
            print("To install ffmpeg on Linux:")
            print("  sudo apt update && sudo apt install ffmpeg  # For Debian/Ubuntu")
            print("  sudo yum install ffmpeg  # For CentOS/RHEL")
        return False

def install_video_dependencies():
    """Install required dependencies for video processing"""
    requirements = {
        "moviepy": "1.0.3",
        "numpy": None,  # Let pip determine the compatible version
        "ffmpeg-python": "0.2.0", 
        "pillow": None  # Let pip determine the compatible version
    }
    
    # Check pip
    if not check_pip():
        return False
    
    # Install Python packages
    all_installed = True
    for package, version in requirements.items():
        if not install_package(package, version):
            all_installed = False
    
    # Check for ffmpeg
    ffmpeg_installed = check_ffmpeg()
    
    return all_installed and ffmpeg_installed

def install_caption_dependencies():
    """Install required dependencies for video captioning"""
    # First install video dependencies
    if not install_video_dependencies():
        print("⚠️ Warning: Some video dependencies could not be installed.")
    
    # Install whisper for transcription
    try:
        print("Installing OpenAI Whisper (this may take a while)...")
        subprocess.run([sys.executable, "-m", "pip", "install", "openai-whisper"], 
                      check=True)
        print("✅ Successfully installed OpenAI Whisper")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install OpenAI Whisper: {str(e)}")
        return False

def main():
    """Main function"""
    print("=== Video Processing Dependencies Installer ===\n")
    
    # Ask what to install
    print("What would you like to install?")
    print("1. Basic video processing dependencies (MoviePy, numpy, ffmpeg-python)")
    print("2. All dependencies including captioning (adds OpenAI Whisper)")
    
    choice = input("Enter your choice (1 or 2): ")
    
    if choice == "1":
        success = install_video_dependencies()
    elif choice == "2":
        success = install_caption_dependencies()
    else:
        print("Invalid choice. Please enter 1 or 2.")
        return
    
    # Print summary
    if success:
        print("\n✅ All dependencies installed successfully!")
    else:
        print("\n⚠️ Some dependencies could not be installed. Please check the messages above.")
    
    # Check ffmpeg regardless of success
    check_ffmpeg()
    
    print("\nYou can now use the video processing features.")

if __name__ == "__main__":
    main() 