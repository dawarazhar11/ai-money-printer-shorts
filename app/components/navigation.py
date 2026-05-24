import streamlit as st
from pathlib import Path
import json
from .progress import render_progress_bar

def get_workflow_steps():
    """Return the list of workflow steps in order"""
    return [
        {
            "name": "Settings",
            "icon": "⚙️",
            "path": "pages/1_Settings.py"
        },
        {
            "name": "Blueprint Setup",
            "icon": "📝",
            "path": "pages/2_Blueprint.py"
        },
        {
            "name": "Script Segmentation",
            "icon": "✂️",
            "path": "pages/3_Script_Segmentation.py"
        },
        {
            "name": "B-Roll Prompts",
            "icon": "🔍",
            "path": "pages/4_BRoll_Prompts.py"
        },
        {
            "name": "A-Roll Video Production",
            "icon": "🎥",
            "path": "pages/5A_ARoll_Video_Production.py"
        },
        {
            "name": "B-Roll Video Production",
            "icon": "🎬",
            "path": "pages/5B_BRoll_Video_Production.py"
        },
        {
            "name": "Video Assembly",
            "icon": "🇯️",
            "path": "pages/6_Video_Assembly.py"
        },
        {
            "name": "Caption The Dreams",
            "icon": "💬",
            "path": "pages/7_Caption_The_Dreams.py"
        },
        {
            "name": "Social Media Upload",
            "icon": "🚀",
            "path": "pages/8_Social_Media_Upload.py"
        }
    ]

def get_step_progress():
    """Get the progress status of each step"""
    progress = {}
    progress_file = Path("config/user_data/progress.json")
    
    if progress_file.exists():
        with open(progress_file, "r") as f:
            progress = json.load(f)
    
    return progress

def render_workflow_navigation():
    """Render the workflow navigation in the sidebar"""
    # Render logo and app name
    st.sidebar.title("🎬 ReelForge")
    st.sidebar.caption("AI Video Shorts Generator")
    
    # Render progress bar
    render_progress_bar()
    
    # Navigation steps
    st.sidebar.divider()
    st.sidebar.subheader("Workflow Steps")
    
    steps = get_workflow_steps()
    progress = get_step_progress()
    
    for i, step in enumerate(steps):
        step_id = f"step_{i}"
        is_complete = progress.get(step_id, False)
        
        # Show checkmark if step is complete
        if is_complete:
            label = f"{step['icon']} {step['name']} ✅"
        else:
            label = f"{step['icon']} {step['name']}"
        
        if st.sidebar.button(label, key=f"nav_{i}"):
            st.switch_page(step["path"])
    
    st.sidebar.divider()
    
    # Home button
    if st.sidebar.button("🏠 Back to Home"):
        st.switch_page("Home.py")

def render_step_navigation(current_step, next_step_path=None, prev_step_path=None):
    """Render navigation buttons for moving between steps"""
    col1, col2 = st.columns(2)
    
    # Previous button
    if prev_step_path and col1.button("← Previous Step", use_container_width=True):
        st.switch_page(prev_step_path)
    
    # Next button
    if next_step_path and col2.button("Next Step →", use_container_width=True, type="primary"):
        # Mark current step as complete
        from utils.session_state import mark_step_complete
        mark_step_complete(f"step_{current_step}")
        st.switch_page(next_step_path)
