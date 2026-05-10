"""Replicate service — wraps utils/replicate_api.py with tenacity retries."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from tenacity import retry, stop_after_attempt, wait_random_exponential

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.replicate")


class ReplicateService:
    """Thin service over the replicate Python SDK."""

    def _get_token(self) -> str:
        token = config_manager.config.replicate_api_token
        if not token:
            import os
            token = os.environ.get("REPLICATE_API_TOKEN", "")
        if not token:
            raise ValueError("REPLICATE_API_TOKEN is not configured")
        return token

    @retry(stop=stop_after_attempt(5), wait=wait_random_exponential(multiplier=1, min=2, max=30), reraise=True)
    def _run(self, model_id: str, inputs: dict) -> Any:
        import replicate as _replicate
        import os
        os.environ["REPLICATE_API_TOKEN"] = self._get_token()
        output = _replicate.run(model_id, input=inputs)
        return output

    def generate_video(
        self,
        prompt: str,
        model_key: str = "wan_2_1_t2v_480p",
        extra_inputs: Optional[dict] = None,
        output_dir: Optional[Path] = None,
        segment_id: str = "segment",
    ) -> MediaAsset:
        from app.utils.replicate_api import AVAILABLE_MODELS

        model_info = AVAILABLE_MODELS.get(model_key)
        if model_info is None:
            raise ValueError(f"Unknown Replicate model: {model_key}")
        model_id = model_info["id"]

        inputs = {"prompt": prompt}
        if extra_inputs:
            inputs.update(extra_inputs)

        logger.info(f"Running Replicate model={model_key} prompt={prompt[:60]!r}")
        output = self._run(model_id, inputs)

        if output is None:
            raise RuntimeError("Replicate returned no output")

        output_url = output[0] if isinstance(output, (list, tuple)) else str(output)
        logger.info(f"Replicate output url={output_url}")

        dest = self._download(output_url, output_dir, segment_id)
        return MediaAsset(file_path=dest, mime_type="video/mp4", metadata={"model_key": model_key, "output_url": output_url})

    @retry(stop=stop_after_attempt(3), wait=wait_random_exponential(multiplier=1, min=1, max=10), reraise=True)
    def _download(self, url: str, output_dir: Optional[Path], segment_id: str) -> str:
        import requests, tempfile, shutil
        resp = requests.get(url, stream=True, timeout=120)
        resp.raise_for_status()
        suffix = ".mp4"
        if output_dir:
            dest = Path(output_dir) / f"{segment_id}{suffix}"
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            return str(dest)
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        for chunk in resp.iter_content(chunk_size=8192):
            tmp.write(chunk)
        tmp.close()
        return tmp.name


replicate_service = ReplicateService()
