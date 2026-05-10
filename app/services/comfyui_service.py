import json
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import requests

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset, ProgressEvent
from app.services.workflows import resolve

logger = get_logger("services.comfyui_service")

try:
    from tenacity import retry, stop_after_attempt, wait_random_exponential
    _TENACITY_AVAILABLE = True
except ImportError:
    _TENACITY_AVAILABLE = False


def _submit_prompt(api_url: str, workflow: dict) -> str:
    resp = requests.post(f"{api_url}/prompt", json={"prompt": workflow}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    prompt_id = data.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"No prompt_id in ComfyUI response: {data}")
    return prompt_id


def _poll_history(api_url: str, prompt_id: str, timeout: int = 600) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{api_url}/history/{prompt_id}", timeout=10)
        if resp.status_code == 200:
            history = resp.json()
            if prompt_id in history:
                return history[prompt_id]
        time.sleep(3)
    raise TimeoutError(f"ComfyUI job {prompt_id} timed out after {timeout}s")


def _prepare_workflow(template_path: Path, prompt: str, negative_prompt: str, resolution: str) -> dict:
    workflow = json.loads(template_path.read_text())
    width, height = (map(int, resolution.split("x")) if "x" in resolution else (1080, 1920))
    for node in workflow.values():
        inputs = node.get("inputs", {})
        if "prompt" in inputs:
            inputs["prompt"] = prompt
        if "negative" in inputs:
            inputs["negative"] = negative_prompt
        title = node.get("_meta", {}).get("title", "")
        if "text" in inputs and "CLIPTextEncode" in node.get("class_type", ""):
            inputs["text"] = prompt if "Positive" in title else negative_prompt
        if "width" in inputs:
            inputs["width"] = width
        if "height" in inputs:
            inputs["height"] = height
    return workflow


def _extract_output_files(job: dict) -> list:
    files = []
    for node_output in job.get("outputs", {}).values():
        for key in ("images", "videos", "gifs"):
            for item in node_output.get(key, []):
                if "filename" in item:
                    files.append(item["filename"])
    return files


def _download_file(api_url: str, filename: str, output_path: str) -> None:
    resp = requests.get(f"{api_url}/view?filename={filename}", timeout=120)
    resp.raise_for_status()
    Path(output_path).write_bytes(resp.content)


class ComfyUIService:
    def _image_url(self) -> str:
        return config_manager.config.comfyui_image_api_url

    def _video_url(self) -> str:
        return config_manager.config.comfyui_video_api_url

    def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        workflow_name: str = "image_homepc",
        resolution: str = "1080x1920",
        output_path: Optional[str] = None,
        on_progress: Optional[Callable[[ProgressEvent], None]] = None,
    ) -> MediaAsset:
        return self._generate(
            prompt, negative_prompt, workflow_name, resolution,
            output_path, on_progress, self._image_url(), "image"
        )

    def generate_video(
        self,
        prompt: str,
        negative_prompt: str = "",
        workflow_name: str = "wan",
        resolution: str = "1080x1920",
        output_path: Optional[str] = None,
        on_progress: Optional[Callable[[ProgressEvent], None]] = None,
    ) -> MediaAsset:
        return self._generate(
            prompt, negative_prompt, workflow_name, resolution,
            output_path, on_progress, self._video_url(), "video"
        )

    def _generate(self, prompt, negative_prompt, workflow_name, resolution,
                  output_path, on_progress, api_url, asset_type) -> MediaAsset:
        wpath = resolve(workflow_name)
        if wpath is None:
            raise FileNotFoundError(f"Workflow not found: {workflow_name}")

        workflow = _prepare_workflow(wpath, prompt, negative_prompt, resolution)
        logger.info("Submitting ComfyUI %s job: workflow=%s", asset_type, workflow_name)
        prompt_id = _submit_prompt(api_url, workflow)
        logger.info("ComfyUI job submitted: prompt_id=%s", prompt_id)

        if on_progress:
            on_progress(ProgressEvent("progress", 0.1, f"Submitted: {prompt_id}"))

        job = _poll_history(api_url, prompt_id)

        if on_progress:
            on_progress(ProgressEvent("progress", 0.9, "Downloading output"))

        files = _extract_output_files(job)
        if not files:
            raise RuntimeError(f"ComfyUI job {prompt_id} produced no output files")

        if output_path is None:
            ext = ".png" if asset_type == "image" else ".mp4"
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            output_path = tmp.name
            tmp.close()

        _download_file(api_url, files[0], output_path)
        logger.info("ComfyUI output saved: %s", output_path)

        if on_progress:
            on_progress(ProgressEvent("complete", 1.0, "Done"))

        return MediaAsset(path=output_path, asset_type=asset_type)

    def submit_async(self, prompt: str, negative_prompt: str = "",
                     workflow_name: str = "image_homepc", resolution: str = "1080x1920",
                     use_video_url: bool = False) -> str:
        """Submit a job and return prompt_id without waiting for completion."""
        wpath = resolve(workflow_name)
        if wpath is None:
            raise FileNotFoundError(f"Workflow not found: {workflow_name}")
        workflow = _prepare_workflow(wpath, prompt, negative_prompt, resolution)
        api_url = self._video_url() if use_video_url else self._image_url()
        logger.info("Submitting async ComfyUI job: workflow=%s", workflow_name)
        return _submit_prompt(api_url, workflow)

    def check_job_status(self, prompt_id: str, use_video_url: bool = False) -> dict:
        api_url = self._video_url() if use_video_url else self._image_url()
        resp = requests.get(f"{api_url}/history/{prompt_id}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
        return {}


comfyui_service = ComfyUIService()
