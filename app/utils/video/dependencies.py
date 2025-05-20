#!/usr/bin/env python3
"""
Direct installer for video processing dependencies
"""

import subprocess
import sys
import os
import platform

def check_dependency(package_name, required_version=None):
    """Check if a package is installed with the required version"""
    try:
        # Try to import the package
        module = __import__(package_name)
        
        # Get the installed version
        installed_version = getattr(module, '__version__', 'unknown')
        
        if required_version and installed_version != required_version:
            print(f"⚠️ {package_name} is installed but version mismatch: {installed_version} (required: {required_version})")
            return False
        
        print(f"✅ {package_name} is installed (version: {installed_version})")
        return True
    except ImportError:
        print(f"❌ {package_name} is not installed")
        return False

def check_ffmpeg():
    """Check if ffmpeg is installed on the system"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"], 
            capture_output=True, 
            text=True
        )
        if result.returncode == 0:
            print(f"✅ ffmpeg is installed: {result.stdout.splitlines()[0]}")
            return True
        else:
            print("❌ ffmpeg is not installed or not in PATH")
            return False
    except FileNotFoundError:
        print("❌ ffmpeg is not installed or not in PATH")
        return False

def install_package(package_spec):
    """Install a Python package with proper version specification"""
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install", package_spec
        ])
        print(f"✅ Successfully installed {package_spec}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package_spec}: {e}")
        return False

def main():
    print("Checking dependencies for video processing...")
    
    # Check required Python packages
    moviepy_ok = check_dependency("moviepy")
    numpy_ok = check_dependency("numpy")
    ffmpeg_python_ok = check_dependency("ffmpeg_python")
    pillow_ok = check_dependency("PIL")
    
    # Check for ffmpeg
    ffmpeg_ok = check_ffmpeg()
    
    # List missing packages
    missing_packages = []
    if not moviepy_ok:
        missing_packages.append("moviepy==1.0.3")
    if not numpy_ok:
        missing_packages.append("numpy")
    if not ffmpeg_python_ok:
        missing_packages.append("ffmpeg-python==0.2.0")
    if not pillow_ok:
        missing_packages.append("pillow")
    
    if missing_packages:
        print("\nMissing packages:")
        for pkg in missing_packages:
            print(f"  - {pkg}")
        
        # Ask user if they want to install missing packages
        user_input = input("Do you want to install missing packages? (y/n): ")
        if user_input.lower() == 'y':
            for package in missing_packages:
                install_package(package)
        else:
            print("Skipping package installation.")
    
    # Check if all dependencies are installed after installation
    has_errors = False
    if not check_dependency("moviepy") or not check_dependency("numpy") or \
       not check_dependency("ffmpeg_python") or not check_dependency("PIL") or \
       not check_ffmpeg():
        has_errors = True
    
    if has_errors:
        print("❌ Some dependencies are missing.")
        print("\nPlease install dependencies manually with:")
        print("  pip install moviepy==1.0.3 numpy ffmpeg-python==0.2.0 pillow")
        print("\nAnd install ffmpeg from your system's package manager:")
        
        if platform.system() == "Darwin":  # macOS
            print("  brew install ffmpeg")
        elif platform.system() == "Linux":
            print("  sudo apt-get install ffmpeg  # For Debian/Ubuntu")
            print("  sudo dnf install ffmpeg     # For Fedora/RHEL")
        elif platform.system() == "Windows":
            print("  Download from https://ffmpeg.org/download.html")
    else:
        print("\n✅ All dependencies are installed successfully!")

if __name__ == "__main__":
    main() 