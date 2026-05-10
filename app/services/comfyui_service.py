"""ComfyUI service — wraps comfyui helpers with tenacity retries and ProgressEvent emissions."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Optional

import requests
from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset, ProgressEvent
from app.services.workflows import resolve

logger = get_logger("services.comfyui")

_COMPLETED_STATUSES = {"completed", "success", "done"}
_FAILED_STATUSES = {"failed", "error", "cancelled"}


class ComfyUIService:
    """Service wrapper around the ComfyUI image/video API."""

    @property
    def image_api_url(self) -> str:
        return config_manager.config.comfyui_image_api_url

    @property
    def video_api_url(self) -> str:
        return config_manager.config.comfyui_video_api_url

    @retry(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, min=2, max=30), reraise=True)
    def _submit_prompt(self, api_url: str, workflow: dict, client_id: str = "") -> str:
        payload = {"prompt": workflow}
        if client_id:
            payload["client_id"] = client_id
        resp = requests.post(f"{api_url}/prompt", json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        prompt_id = data.get("prompt_id")
        if not prompt_id:
            raise RuntimeError(f"ComfyUI returned no prompt_id: {data}")
        return prompt_id

    @retry(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, min=2, max=20), reraise=True)
    def _get_history(self, api_url: str, prompt_id: str) -> dict:
        resp = requests.get(f"{api_url}/history/{prompt_id}", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _poll_until_done(
        self,
        api_url: str,
        prompt_id: str,
        progress_cb: Optional[Callable[[ProgressEvent], None]] = None,
        max_wait: int = 600,
    ) -> dict:
        elapsed = 0
        interval = 5
        while elapsed < max_wait:
            history = self._get_history(api_url, prompt_id)
            entry = history.get(prompt_id, {})
            status = entry.get("status", {})
            completed = status.get("completed", False)
            status_str = status.get("status_str", "").lower()

            if progress_cb:
                progress_cb(ProgressEvent(step="comfyui", progress=min(0.9, elapsed / max_wait), message=status_str))

            if completed or status_str in _COMPLETED_STATUSES:
                return entry
            if status_str in _FAILED_STATUSES:
                raise RuntimeError(f"ComfyUI job failed: {prompt_id}")

            logger.info(f"ComfyUI prompt {prompt_id}: {status_str} ({elapsed}s)")
            time.sleep(interval)
            elapsed += interval

        raise TimeoutError(f"ComfyUI timed out after {max_wait}s for prompt {prompt_id}")

    def _extract_output_file(self, api_url: str, history_entry: dict) -> Optional[str]:
        """Walk the history outputs to find the first image/video file."""
        outputs = history_entry.get("outputs", {})
        for node_id, node_out in outputs.items():
            for key in ("images", "videos", "files"):
                items = node_out.get(key, [])
                if items:
                    item = items[0]
                    filename = item.get("filename") or item.get("name")
                    subfolder = item.get("subfolder", "")
                    if filename:
                        return self._download_output(api_url, filename, subfolder)
        return None

    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, min=1, max=10), reraise=True)
    def _download_output(self, api_url: str, filename: str, subfolder: str = "") -> str:
        import tempfile
        params = {"filename": filename, "type": "output"}
        if subfolder:
            params["subfolder"] = subfolder
        resp = requests.get(f"{api_url}/view", params=params, timeout=60)
        resp.raise_for_status()
        suffix = Path(filename).suffix or ".png"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp.write(resp.content)
        tmp.close()
        return tmp.name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def generate_image(
        self,
        prompt: str,
        workflow_name: str = "image_homepc",
        output_dir: Optional[Path] = None,
        segment_id: str = "segment",
        progress_cb: Optional[Callable[[ProgressEvent], None]] = None,
    ) -> MediaAsset:
        workflow_path = resolve(workflow_name)
        if workflow_path is None:
            raise FileNotFoundError(f"Workflow not found: {workflow_name}")

        workflow = json.loads(workflow_path.read_text())
        self._inject_prompt(workflow, prompt)

        logger.info(f"Submitting ComfyUI image job workflow={workflow_name}")
        prompt_id = self._submit_prompt(self.image_api_url, workflow)
        logger.info(f"ComfyUI prompt_id={prompt_id}")

        history_entry = self._poll_until_done(self.image_api_url, prompt_id, progress_cb)
        output_file = self._extract_output_file(self.image_api_url, history_entry)

        if output_file is None:
            raise RuntimeError("ComfyUI finished but no output file found")

        if output_dir:
            dest = Path(output_dir) / f"{segment_id}{Path(output_file).suffix}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            import shutil
            shutil.move(output_file, dest)
            output_file = str(dest)

        mime = "video/mp4" if output_file.endswith(".mp4") else "image/png"
        return MediaAsset(file_path=output_file, mime_type=mime, metadata={"prompt_id": prompt_id})

    def _inject_prompt(self, workflow: dict, prompt: str) -> None:
        """Best-effort: set positive prompt text in the first CLIPTextEncode node."""
        for node in workflow.values():
            if not isinstance(node, dict):
                continue
            class_type = node.get("class_type", "")
            if "CLIPTextEncode" in class_type:
                inputs = node.get("inputs", {})
                if "text" in inputs and "negative" not in class_type.lower():
                    inputs["text"] = prompt
                    return


comfyui_service = ComfyUIService()
