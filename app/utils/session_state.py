import streamlit as st
import json
from pathlib import Path
import os

def get_settings():
    """Load settings from session state or file"""
    if "settings" in st.session_state:
        return st.session_state["settings"]
    
    config_file = Path("config/user_data/project_settings.json")
    if config_file.exists():
        with open(config_file, "r") as f:
            settings = json.load(f)
            st.session_state["settings"] = settings
            return settings
    
    # No settings found, redirect to settings page
    st.warning("Please configure project settings before continuing.")
    st.switch_page("pages/1_Settings.py")
    return None

def check_step_completion(step_name):
    """Check if a specific step has been completed"""
    progress_file = Path("config/user_data/progress.json")
    
    if progress_file.exists():
        with open(progress_file, "r") as f:
            progress = json.load(f)
            return progress.get(step_name, False)
    
    return False

def mark_step_complete(step_name):
    """Mark a step as complete in the progress tracker"""
    progress_file = Path("config/user_data/progress.json")
    progress = {}
    
    if progress_file.exists():
        with open(progress_file, "r") as f:
            progress = json.load(f)
    
    progress[step_name] = True
    
    # Save progress
    with open(progress_file, "w") as f:
        json.dump(progress, f, indent=4)
    
    return True

def get_project_path():
    """Get the path for project assets"""
    settings = get_settings()
    if not settings:
        return None
    
    # Create a project directory using the project name
    project_name = settings.get("project_name", "my_project")
    project_name = project_name.lower().replace(" ", "_")
    
    project_dir = Path("config/user_data") / project_name
    project_dir.mkdir(parents=True, exist_ok=True)
    
    return project_dir 