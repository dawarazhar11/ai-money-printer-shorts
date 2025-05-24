"""
Audio processing utilities for AI Money Printer Shorts
"""

# Import key functions to make them available directly
try:
    from .transcription import check_module_availability, get_available_engines, transcribe_video
except ImportError:
    print("Warning: Could not import transcription module") 