#!/usr/bin/env python3
"""
Test script to verify that the captions module is working correctly
"""

import os
import sys
import traceback
from pathlib import Path

# Add the parent directory to sys.path
app_dir = Path(__file__).parent.absolute()
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))
    print(f"Added {app_dir} to path")

try:
    print("Attempting to import captions module...")
    from utils.video.captions import (
        check_dependencies,
        get_available_caption_styles,
        CAPTION_STYLES,
        TYPOGRAPHY_EFFECTS
    )
    print("✅ Successfully imported caption modules")
    
    # Check available styles
    styles = get_available_caption_styles()
    print(f"Available caption styles: {', '.join(styles.keys())}")
    
    # Check dependencies
    deps = check_dependencies()
    if deps["all_available"]:
        print("✅ All required dependencies are available")
    else:
        print(f"❌ Missing dependencies: {', '.join(deps['missing'])}")
    
    print("Captions module test completed successfully")
    
except ImportError as e:
    print(f"❌ Error importing caption modules: {e}")
    print(traceback.format_exc())
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    print(traceback.format_exc())
    sys.exit(1) 