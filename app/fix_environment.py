#!/usr/bin/env python3
"""
Environment Setup and Verification Script for AI Money Printer
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {text} ".center(60, '='))
    print("=" * 60)

def print_status(text, success=True):
    """Print a status message"""
    if success:
        print(f"✅ {text}")
    else:
        print(f"❌ {text}")

def run_command(command):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(command, shell=True, check=True, 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

def check_venv():
    """Check if running in a virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)
    if in_venv:
        print_status("Running in virtual environment")
        return True
    else:
        print_status("Not running in virtual environment", False)
        return False

def check_python_packages():
    """Check if the required Python packages are installed"""
    print_header("Checking Python Packages")
    
    required_packages = [
        "streamlit>=1.30.0",
        "watchdog>=3.0.0",
        "pillow>=10.0.0",
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        "matplotlib>=3.7.0",
        "pydub>=0.25.1",
        "moviepy>=1.0.3",
        "python-dotenv>=1.0.0",
        "requests>=2.28.1",
        "opencv-python>=4.7.0",
        "websocket-client>=1.6.0",
        "ffmpeg-python"
    ]
    
    missing_packages = []
    
    for package_req in required_packages:
        package_name = package_req.split(">=")[0].split("==")[0]
        try:
            __import__(package_name.replace("-", "_"))
            print_status(f"Package {package_name} is installed")
        except ImportError:
            print_status(f"Package {package_name} is NOT installed", False)
            missing_packages.append(package_req)
    
    return missing_packages

def check_ffmpeg():
    """Check if ffmpeg is installed"""
    print_header("Checking FFMPEG")
    
    success, output = run_command("which ffmpeg")
    if success:
        print_status(f"FFMPEG found at: {output.strip()}")
        return True
    else:
        print_status("FFMPEG not found", False)
        return False

def check_directory_structure():
    """Check if the directory structure is correct"""
    print_header("Checking Directory Structure")
    
    # Get the current directory
    current_dir = os.path.abspath(os.path.dirname(__file__))
    print(f"Current directory: {current_dir}")
    
    # Check if important directories exist
    required_dirs = ["pages", "components", "utils"]
    for d in required_dirs:
        path = os.path.join(current_dir, d)
        if os.path.isdir(path):
            print_status(f"Directory {d} exists")
        else:
            print_status(f"Directory {d} does NOT exist", False)
    
    # Check the structure
    if "AI-Money-Printer-Shorts" in current_dir:
        if current_dir.endswith("app"):
            print_status("Correct directory structure (inside app directory)")
            return True
        else:
            print_status("Not in the app directory", False)
            return False
    else:
        print_status("Not in the AI-Money-Printer-Shorts directory", False)
        return False

def fix_missing_packages(missing_packages):
    """Install missing Python packages"""
    if not missing_packages:
        print("No missing packages to install.")
        return True
    
    print_header("Installing Missing Packages")
    for package in missing_packages:
        print(f"Installing {package}...")
        success, output = run_command(f"pip install {package}")
        if success:
            print_status(f"Installed {package}")
        else:
            print_status(f"Failed to install {package}", False)
            print(output)
            return False
    
    return True

def fix_ffmpeg():
    """Install FFMPEG"""
    print_header("Installing FFMPEG")
    
    if sys.platform == "darwin":  # Mac
        success, output = run_command("brew install ffmpeg")
        if success:
            print_status("Installed FFMPEG via Homebrew")
            return True
        else:
            print_status("Failed to install FFMPEG", False)
            print(output)
            return False
    elif sys.platform == "linux":  # Linux
        success, output = run_command("sudo apt-get update && sudo apt-get install -y ffmpeg")
        if success:
            print_status("Installed FFMPEG via apt")
            return True
        else:
            print_status("Failed to install FFMPEG", False)
            print(output)
            return False
    else:  # Windows or other
        print("Please install FFMPEG manually:")
        print("1. Download from https://ffmpeg.org/download.html")
        print("2. Add to your PATH")
        return False

def main():
    """Main function"""
    print_header("AI Money Printer Environment Setup")
    
    # Check if running in virtual environment
    in_venv = check_venv()
    
    # Check for required Python packages
    missing_packages = check_python_packages()
    
    # Check for FFMPEG
    has_ffmpeg = check_ffmpeg()
    
    # Check directory structure
    correct_structure = check_directory_structure()
    
    # Fix issues if needed
    if missing_packages and in_venv:
        print("\nWould you like to install missing packages? (y/n)")
        choice = input().lower()
        if choice.startswith('y'):
            fix_missing_packages(missing_packages)
    
    if not has_ffmpeg:
        print("\nWould you like to install FFMPEG? (y/n)")
        choice = input().lower()
        if choice.startswith('y'):
            fix_ffmpeg()
    
    # Print summary
    print_header("Summary")
    if not in_venv:
        print("⚠️ Please activate your virtual environment:")
        print("   source .venv/bin/activate")
    
    if missing_packages:
        print("⚠️ Some packages are missing. Install with:")
        print(f"   pip install {' '.join(missing_packages)}")
    
    if not has_ffmpeg:
        print("⚠️ FFMPEG is not installed. Please install it for video processing.")
    
    if not correct_structure:
        print("⚠️ Directory structure may be incorrect.")
        print("   Make sure you are running from the app directory.")
    
    if in_venv and not missing_packages and has_ffmpeg and correct_structure:
        print("🎉 Everything looks good! You can run the app with:")
        print("   streamlit run pages/6_Video_Assembly.py")

if __name__ == "__main__":
    main() 