import os
import sys
import unittest
from pathlib import Path
import tempfile
import shutil
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import functions from our implementation
from pages.6_Video_Assembly import create_assembly_sequence, resize_video

# Mock MoviePy for testing
try:
    import moviepy.editor as mp
except ImportError:
    print("MoviePy not installed. Some tests will be skipped.")
    mp = None

class TestVideoAssembly(unittest.TestCase):
    def setUp(self):
        # Create temp directory for test files
        self.test_dir = tempfile.mkdtemp()
        
        # Create mock segments
        self.segments = [
            {"type": "A-Roll", "content": "This is A-Roll segment 1"},
            {"type": "B-Roll", "content": "This is B-Roll segment 1"},
            {"type": "A-Roll", "content": "This is A-Roll segment 2"},
            {"type": "B-Roll", "content": "This is B-Roll segment 2"},
            {"type": "A-Roll", "content": "This is A-Roll segment 3"},
            {"type": "A-Roll", "content": "This is A-Roll segment 4"}
        ]
        
        # Create mock content status
        self.content_status = {
            "aroll": {
                "segment_0": {"status": "complete", "file_path": f"{self.test_dir}/aroll_0.mp4"},
                "segment_2": {"status": "complete", "file_path": f"{self.test_dir}/aroll_2.mp4"},
                "segment_4": {"status": "complete", "file_path": f"{self.test_dir}/aroll_4.mp4"},
                "segment_5": {"status": "complete", "file_path": f"{self.test_dir}/aroll_5.mp4"}
            },
            "broll": {
                "segment_0": {"status": "complete", "file_path": f"{self.test_dir}/broll_0.mp4"},
                "segment_1": {"status": "complete", "file_path": f"{self.test_dir}/broll_1.mp4"}
            }
        }
        
        # Create dummy test files
        for segment_type in ["aroll", "broll"]:
            for segment_id, data in self.content_status[segment_type].items():
                # Create empty file
                with open(data["file_path"], "wb") as f:
                    f.write(b"test")
    
    def tearDown(self):
        # Remove temp directory
        shutil.rmtree(self.test_dir)
    
    def test_create_assembly_sequence(self):
        """Test that assembly sequence is created correctly"""
        result = create_assembly_sequence(self.segments, self.content_status)
        
        # Verify result status
        self.assertEqual(result["status"], "success")
        
        # Verify sequence structure
        sequence = result["sequence"]
        self.assertIsInstance(sequence, list)
        
        # Verify the first item is A-Roll
        self.assertEqual(sequence[0]["type"], "aroll_full")
        self.assertEqual(sequence[0]["segment_id"], "segment_0")
        
        # Verify the second item is B-Roll with A-Roll audio
        self.assertEqual(sequence[1]["type"], "broll_with_aroll_audio")
        self.assertEqual(sequence[1]["broll_segment_id"], "segment_0")
        self.assertEqual(sequence[1]["aroll_segment_id"], "segment_2")
        
        # Verify the third item is B-Roll with A-Roll audio
        self.assertEqual(sequence[2]["type"], "broll_with_aroll_audio")
        self.assertEqual(sequence[2]["broll_segment_id"], "segment_1")
        self.assertEqual(sequence[2]["aroll_segment_id"], "segment_4")
        
        # Verify the fourth item is A-Roll
        self.assertEqual(sequence[3]["type"], "aroll_full")
        self.assertEqual(sequence[3]["segment_id"], "segment_5")
    
    def test_empty_segments(self):
        """Test handling of empty segments"""
        result = create_assembly_sequence([], self.content_status)
        self.assertEqual(result["status"], "error")
    
    def test_no_aroll(self):
        """Test handling of missing A-Roll segments"""
        empty_content_status = {"aroll": {}, "broll": self.content_status["broll"]}
        result = create_assembly_sequence(self.segments, empty_content_status)
        self.assertEqual(result["status"], "error")
    
    @unittest.skipIf(mp is None, "MoviePy not installed")
    def test_resize_video(self):
        """Test that video resizing works correctly (if MoviePy is available)"""
        # This test requires MoviePy to be installed
        # Since we can't create actual video files easily in a test,
        # we'll just test that the function doesn't raise exceptions
        try:
            # Create a tiny clip for testing
            clip = mp.ColorClip(size=(640, 480), color=(0, 0, 0), duration=1)
            
            # Test resize to portrait (9:16)
            resized = resize_video(clip, (1080, 1920))
            self.assertEqual(resized.size, (1080, 1920))
            
            # Test resize to landscape (16:9)
            resized = resize_video(clip, (1920, 1080))
            self.assertEqual(resized.size, (1920, 1080))
        except Exception as e:
            self.fail(f"resize_video raised exception: {str(e)}")

if __name__ == "__main__":
    unittest.main() 