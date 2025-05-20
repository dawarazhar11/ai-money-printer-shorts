#!/usr/bin/env python3
import subprocess
import sys
import os
import pkg_resources

def check_pip():
    """Check if pip is installed and accessible"""
    try:
        import pip
        print("✅ pip is installed")
        return True
    except ImportError:
        print("❌ pip is not installed")
        return False

def check_virtual_env():
    """Check if running in a virtual environment"""
    is_venv = sys.prefix != sys.base_prefix
    if is_venv:
        print(f"✅ Running in virtual environment: {sys.prefix}")
    else:
        print("❌ Not running in a virtual environment")
    return is_venv

def install_package(package_name, version=None):
    """Install a package using pip"""
    pkg_spec = f"{package_name}=={version}" if version else package_name
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_spec])
        print(f"✅ Installed {pkg_spec}")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {pkg_spec}")
        return False

def check_and_install_dependencies():
    """Check and install required dependencies for video processing"""
    dependencies = {
        "moviepy": "1.0.3",
        "numpy": "1.26.4",
        "ffmpeg-python": "0.2.0",
        "decorator": "4.4.2"
    }
    
    # Check installed packages
    installed_packages = {pkg.key: pkg.version for pkg in pkg_resources.working_set}
    missing_or_wrong_version = []
    
    for package, version in dependencies.items():
        if package in installed_packages:
            installed_version = installed_packages[package]
            if installed_version != version:
                print(f"⚠️ {package} version mismatch: installed {installed_version}, required {version}")
                missing_or_wrong_version.append((package, version))
            else:
                print(f"✅ {package} {version} is installed")
        else:
            print(f"❌ {package} is not installed")
            missing_or_wrong_version.append((package, version))
    
    # Install missing packages
    for package, version in missing_or_wrong_version:
        install_package(package, version)
    
    # Check if ffmpeg is available
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ ffmpeg is installed: {result.stdout.splitlines()[0]}")
        else:
            print("❌ ffmpeg is not installed or not in PATH")
            print("Please install ffmpeg: https://ffmpeg.org/download.html")
    except FileNotFoundError:
        print("❌ ffmpeg is not installed or not in PATH")
        print("Please install ffmpeg: https://ffmpeg.org/download.html")

if __name__ == "__main__":
    print("Checking dependencies for video processing...")
    check_pip()
    check_virtual_env()
    check_and_install_dependencies()
    print("Dependency check completed.") 