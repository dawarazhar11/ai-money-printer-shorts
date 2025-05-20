"""
Video assembly and processing utilities for AI Money Printer Shorts
"""

# Import primary assembly components
from .assembly import (
    assemble_video,
    check_file,
    resize_video,
    MOVIEPY_AVAILABLE
)

# Import simple assembly fallback
try:
    from .simple_assembly import simple_assemble_video
except ImportError:
    simple_assemble_video = None

__all__ = [
    'assemble_video',
    'check_file',
    'resize_video',
    'MOVIEPY_AVAILABLE',
    'simple_assemble_video'
] 