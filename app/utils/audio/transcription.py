#!/usr/bin/env python3
"""
Transcription module for AI Money Printer Shorts

Provides functions to transcribe audio from videos using
either OpenAI Whisper or Vosk, depending on what's available.
"""

import os
import sys
import tempfile
import json
import subprocess
from pathlib import Path
import importlib.util

# Add the parent directory to sys.path
app_root = Path(__file__).parent.parent.parent.absolute()
if str(app_root) not in sys.path:
    sys.path.insert(0, str(app_root))
    print(f"Added {app_root} to path from transcription module")

# Try to import moviepy
try:
    import moviepy.editor as mp
except ImportError:
    print("MoviePy not found. Please install it to use transcription features.")

def check_module_availability(module_name):
    """
    Check if a Python module is available for import
    
    Args:
        module_name: Name of the module to check
        
    Returns:
        bool: True if module is available, False otherwise
    """
    try:
        # Check if module is already imported
        if module_name in sys.modules:
            return True
            
        # Try to find the module specification
        spec = importlib.util.find_spec(module_name)
        if spec is not None:
            # Try to import it to verify it works
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return True
    except (ImportError, AttributeError, ModuleNotFoundError):
        pass
    
    return False

def get_available_engines():
    """
    Get a list of available transcription engines
    
    Returns:
        list: List of available engine names
    """
    available = []
    
    # Check for OpenAI Whisper
    if check_module_availability("whisper"):
        available.append("whisper")
    
    # Check for Faster Whisper
    if check_module_availability("faster_whisper"):
        available.append("faster_whisper")
    
    # Check for Vosk
    if check_module_availability("vosk"):
        available.append("vosk")
    
    return available

def extract_audio(video_path, output_path=None):
    """
    Extract audio from a video file
    
    Args:
        video_path: Path to the video file
        output_path: Path to save the extracted audio (optional)
        
    Returns:
        str: Path to the extracted audio file
    """
    if not output_path:
        # Create a temporary file with .wav extension
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            output_path = temp_file.name
    
    try:
        # Load the video and extract audio
        video = mp.VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile(output_path, codec='pcm_s16le', verbose=False, logger=None)
        video.close()
        return output_path
    except Exception as e:
        print(f"Error extracting audio: {str(e)}")
        if os.path.exists(output_path):
            os.unlink(output_path)
        return None

def transcribe_with_whisper(audio_path, model_size="base"):
    """
    Transcribe audio using OpenAI Whisper
    
    Args:
        audio_path: Path to the audio file
        model_size: Whisper model size (tiny, base, small, medium, large)
        
    Returns:
        dict: Transcription results
    """
    try:
        import whisper
        
        print(f"Loading Whisper model: {model_size}")
        model = whisper.load_model(model_size)
        
        print("Transcribing audio...")
        result = model.transcribe(
            audio_path,
            word_timestamps=True,
            verbose=False
        )
        
        # Process the result to extract word-level timings
        segments = []
        words = []
        
        for segment in result.get("segments", []):
            segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip()
            })
            
            for word in segment.get("words", []):
                words.append({
                    "word": word["word"].strip(),
                    "start": word["start"],
                    "end": word["end"],
                    "probability": word.get("probability", 1.0)
                })
        
        return {
            "status": "success",
            "engine": "whisper",
            "text": result["text"],
            "segments": segments,
            "words": words
        }
    except ImportError:
        return {"status": "error", "message": "Whisper not installed"}
    except Exception as e:
        return {"status": "error", "message": f"Error transcribing with Whisper: {str(e)}"}

def transcribe_with_faster_whisper(audio_path, model_size="base"):
    """
    Transcribe audio using Faster Whisper
    
    Args:
        audio_path: Path to the audio file
        model_size: Model size (tiny, base, small, medium, large)
        
    Returns:
        dict: Transcription results
    """
    try:
        from faster_whisper import WhisperModel
        
        print(f"Loading Faster Whisper model: {model_size}")
        model = WhisperModel(model_size)
        
        print("Transcribing audio...")
        segments, info = model.transcribe(
            audio_path,
            word_timestamps=True,
            vad_filter=True
        )
        
        # Process the result to extract word-level timings
        segment_list = []
        words_list = []
        full_text = ""
        
        for segment in segments:
            segment_text = segment.text.strip()
            full_text += " " + segment_text
            
            segment_list.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment_text
            })
            
            for word in segment.words:
                words_list.append({
                    "word": word.word.strip(),
                    "start": word.start,
                    "end": word.end,
                    "probability": word.probability
                })
        
        return {
            "status": "success",
            "engine": "faster_whisper",
            "text": full_text.strip(),
            "segments": segment_list,
            "words": words_list
        }
    except ImportError:
        return {"status": "error", "message": "Faster Whisper not installed"}
    except Exception as e:
        return {"status": "error", "message": f"Error transcribing with Faster Whisper: {str(e)}"}

def transcribe_with_vosk(audio_path):
    """
    Transcribe audio using Vosk
    
    Args:
        audio_path: Path to the audio file
        
    Returns:
        dict: Transcription results
    """
    try:
        from vosk import Model, KaldiRecognizer, SetLogLevel
        import wave
        
        # Suppress vosk logs
        SetLogLevel(-1)
        
        # Check for model
        model_path = os.path.join(app_root, "models", "vosk")
        if not os.path.exists(model_path):
            os.makedirs(model_path, exist_ok=True)
            return {"status": "error", "message": f"Vosk model not found. Please download a model to {model_path}"}
        
        # Get the model directories
        model_dirs = [d for d in os.listdir(model_path) if os.path.isdir(os.path.join(model_path, d))]
        if not model_dirs:
            return {"status": "error", "message": f"No Vosk models found in {model_path}"}
        
        # Use the first model
        model_dir = os.path.join(model_path, model_dirs[0])
        print(f"Using Vosk model: {model_dir}")
        
        # Load the model
        model = Model(model_dir)
        
        # Open audio file
        wf = wave.open(audio_path, "rb")
        
        # Create recognizer
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)
        
        # Process the audio
        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part_result = json.loads(rec.Result())
                results.append(part_result)
        
        # Get the final result
        final_result = json.loads(rec.FinalResult())
        results.append(final_result)
        
        # Process results to extract segments and words
        segments = []
        words = []
        full_text = ""
        
        current_offset = 0
        for result in results:
            if "result" in result and result["result"]:
                segment_text = result.get("text", "").strip()
                full_text += " " + segment_text
                
                segment_words = result["result"]
                start_time = segment_words[0]["start"] if segment_words else 0
                end_time = segment_words[-1]["end"] if segment_words else 0
                
                segments.append({
                    "start": start_time,
                    "end": end_time,
                    "text": segment_text
                })
                
                for word_info in segment_words:
                    words.append({
                        "word": word_info["word"],
                        "start": word_info["start"],
                        "end": word_info["end"],
                        "probability": word_info.get("conf", 1.0)
                    })
                
                current_offset = end_time
        
        return {
            "status": "success",
            "engine": "vosk",
            "text": full_text.strip(),
            "segments": segments,
            "words": words
        }
    except ImportError:
        return {"status": "error", "message": "Vosk not installed"}
    except Exception as e:
        return {"status": "error", "message": f"Error transcribing with Vosk: {str(e)}"}

def transcribe_video(video_path, engine="auto", model_size="base"):
    """
    Transcribe a video file using the specified engine
    
    Args:
        video_path: Path to the video file
        engine: Transcription engine to use ("whisper", "faster_whisper", "vosk", or "auto")
        model_size: Model size for Whisper/Faster-Whisper (tiny, base, small, medium, large)
        
    Returns:
        dict: Transcription results
    """
    if not os.path.exists(video_path):
        return {"status": "error", "message": f"Video file not found: {video_path}"}
    
    # Extract audio from video
    audio_path = extract_audio(video_path)
    if not audio_path:
        return {"status": "error", "message": "Failed to extract audio from video"}
    
    try:
        # Determine which engine to use
        available_engines = get_available_engines()
        
        if not available_engines:
            return {
                "status": "error", 
                "message": "No transcription engines available. Please install whisper, faster-whisper, or vosk."
            }
        
        if engine == "auto" or engine not in available_engines:
            # Choose the best available engine
            if "faster_whisper" in available_engines:
                engine = "faster_whisper"
            elif "whisper" in available_engines:
                engine = "whisper"
            else:
                engine = available_engines[0]
        
        print(f"Using transcription engine: {engine}")
        
        # Transcribe using the selected engine
        if engine == "whisper":
            result = transcribe_with_whisper(audio_path, model_size)
        elif engine == "faster_whisper":
            result = transcribe_with_faster_whisper(audio_path, model_size)
        elif engine == "vosk":
            result = transcribe_with_vosk(audio_path)
        else:
            result = {"status": "error", "message": f"Unknown engine: {engine}"}
        
        return result
    finally:
        # Clean up temporary audio file
        if audio_path and os.path.exists(audio_path):
            os.unlink(audio_path)

if __name__ == "__main__":
    # Test the transcription functions
    if len(sys.argv) > 1:
        video_path = sys.argv[1]
        print(f"Transcribing video: {video_path}")
        
        available_engines = get_available_engines()
        print(f"Available engines: {', '.join(available_engines)}")
        
        if available_engines:
            result = transcribe_video(video_path)
            print(f"Transcription result: {result['status']}")
            if result['status'] == 'success':
                print(f"Transcribed text: {result['text'][:100]}...")
                print(f"Word count: {len(result['words'])}")
        else:
            print("No transcription engines available. Please install whisper, faster-whisper, or vosk.")
    else:
        print("Usage: python transcription.py <video_path>") 