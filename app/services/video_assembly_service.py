import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.video_assembly_service")

try:
    from utils.video.simple_assembly import simple_assemble_video, check_ffmpeg, image_to_video
    _SIMPLE_ASSEMBLY_AVAILABLE = True
except ImportError:
    _SIMPLE_ASSEMBLY_AVAILABLE = False
    logger.warning("utils.video.simple_assembly not importable")

try:
    from utils.video.assembly import assemble_video as _moviepy_assemble, MOVIEPY_AVAILABLE
except ImportError:
    _moviepy_assemble = None
    MOVIEPY_AVAILABLE = False


def _ffmpeg_concat(video_files: List[str], output_path: str, audio_path: Optional[str] = None) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        concat_file = f.name
        for vf in video_files:
            escaped = vf.replace("'", "'\\''")
            f.write(f"file '{escaped}'\n")

    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file]
    if audio_path:
        cmd += ["-i", audio_path, "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0"]
    else:
        cmd += ["-c", "copy"]
    cmd.append(output_path)

    result = subprocess.run(cmd, capture_output=True, text=True)
    Path(concat_file).unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg concat failed: {result.stderr}")


class VideoAssemblyService:
    def assemble(
        self,
        sequence: List[dict],
        output_path: str,
        target_resolution: tuple = (1080, 1920),
    ) -> MediaAsset:
        if not sequence:
            raise ValueError("Cannot assemble empty sequence")

        logger.info("Assembling %d clips -> %s", len(sequence), output_path)

        if _SIMPLE_ASSEMBLY_AVAILABLE:
            result = simple_assemble_video(
                sequence=sequence,
                output_path=output_path,
                target_resolution=target_resolution,
            )
            if isinstance(result, dict) and result.get("status") == "success":
                return MediaAsset(path=output_path, asset_type="video")
            if isinstance(result, dict) and result.get("status") == "error":
                raise RuntimeError(result.get("message", "Assembly failed"))

        video_files = [item["video_path"] for item in sequence if Path(item["video_path"]).exists()]
        if not video_files:
            raise RuntimeError("No valid video files in sequence")
        _ffmpeg_concat(video_files, output_path)
        return MediaAsset(path=output_path, asset_type="video")

    def image_to_clip(self, image_path: str, output_path: str, duration: float = 5.0) -> MediaAsset:
        if _SIMPLE_ASSEMBLY_AVAILABLE:
            from utils.video.simple_assembly import image_to_video
            ok = image_to_video(image_path, output_path, duration=duration)
            if ok:
                return MediaAsset(path=output_path, asset_type="video")
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", image_path,
            "-t", str(duration), "-c:v", "libx264", "-pix_fmt", "yuv420p",
            output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"image_to_video failed: {result.stderr}")
        return MediaAsset(path=output_path, asset_type="video", duration=duration)

    def merge_audio(self, video_path: str, audio_path: str, output_path: str) -> MediaAsset:
        cmd = [
            "ffmpeg", "-y", "-i", video_path, "-i", audio_path,
            "-c:v", "copy", "-c:a", "aac", "-map", "0:v:0", "-map", "1:a:0",
            "-shortest", output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"merge_audio failed: {result.stderr}")
        return MediaAsset(path=output_path, asset_type="video")


video_assembly_service = VideoAssemblyService()
