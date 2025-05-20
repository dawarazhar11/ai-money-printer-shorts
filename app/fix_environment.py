#!/usr/bin/env python3
"""
Environment Setup and Verification Script for AI Money Printer
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
import pkg_resources

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

def check_package(package_name):
    """Check if a package is installed and return its version if available"""
    try:
        package = pkg_resources.get_distribution(package_name)
        return True, package.version
    except pkg_resources.DistributionNotFound:
        return False, None

def install_package(package_name, version=None):
    """Install a package using pip"""
    package_spec = package_name
    if version:
        package_spec = f"{package_name}=={version}"
    
    print(f"Installing {package_spec}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package_spec])
    return True

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

def main():
    """Main function"""
    print_header("AI Money Printer Environment Setup")
    
    # Check for Python version
    py_version = sys.version.split()[0]
    print(f"Python version: {py_version}")
    
    # Check for critical packages
    required_packages = {
        "streamlit": "1.31.0",
        "moviepy": "1.0.3",
        "numpy": "1.24.3",
        "opencv-python": "4.8.0.76",
        "ffmpeg-python": None,  # Latest version
        "pillow": None,  # Latest version
        "requests": None,  # Latest version
    }
    
    missing_packages = []
    outdated_packages = []
    
    # Check each package
    for package_name, required_version in required_packages.items():
        installed, version = check_package(package_name)
        
        if not installed:
            print(f"❌ {package_name}: Not installed")
            missing_packages.append((package_name, required_version))
        elif required_version and version != required_version:
            print(f"⚠️ {package_name}: Installed version {version}, required version {required_version}")
            outdated_packages.append((package_name, required_version))
        else:
            print(f"✅ {package_name}: Version {version}")
    
    # Install missing packages
    if missing_packages:
        print("\n----- Installing missing packages -----")
        for package_name, version in missing_packages:
            try:
                install_package(package_name, version)
                print(f"✅ Successfully installed {package_name}")
            except Exception as e:
                print(f"❌ Failed to install {package_name}: {str(e)}")
    
    # Update outdated packages if needed
    if outdated_packages and input("\nUpdate outdated packages? (y/n): ").lower() == 'y':
        print("\n----- Updating outdated packages -----")
        for package_name, version in outdated_packages:
            try:
                install_package(package_name, version)
                print(f"✅ Successfully updated {package_name} to version {version}")
            except Exception as e:
                print(f"❌ Failed to update {package_name}: {str(e)}")
    
    # Check for ffmpeg
    try:
        ffmpeg_path = subprocess.check_output(["which", "ffmpeg"]).decode().strip()
        print(f"\n✅ ffmpeg found at: {ffmpeg_path}")
    except:
        print("\n❌ ffmpeg not found. This is required for video processing.")
        print("   Please install ffmpeg using your system package manager:")
        print("   macOS: brew install ffmpeg")
        print("   Ubuntu/Debian: sudo apt-get install ffmpeg")
        print("   Windows: https://ffmpeg.org/download.html")
    
    print("\n===== Environment check complete =====")
    
    if not missing_packages and not outdated_packages:
        print("✅ All required packages are installed correctly!")
    else:
        print("⚠️ Some packages were installed or updated.")
        print("   Please restart your Streamlit app to apply changes.")

if __name__ == "__main__":
    main() 