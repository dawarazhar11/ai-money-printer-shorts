import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.replicate_service")

try:
    from tenacity import retry, stop_after_attempt, wait_random_exponential
    _TENACITY_AVAILABLE = True
except ImportError:
    _TENACITY_AVAILABLE = False

_APP_DIR = Path(__file__).resolve().parent.parent
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

try:
    from utils.replicate_api import (
        generate_broll_video,
        get_available_models,
        AVAILABLE_MODELS,
    )
    _REPLICATE_UTILS_AVAILABLE = True
except ImportError:
    _REPLICATE_UTILS_AVAILABLE = False
    logger.warning("utils.replicate_api not importable")

try:
    import replicate as _replicate_sdk
    _REPLICATE_SDK_AVAILABLE = True
except ImportError:
    _REPLICATE_SDK_AVAILABLE = False
    logger.warning("replicate SDK not installed — Replicate synthesis unavailable")


class ReplicateService:
    def _ensure_token(self) -> str:
        token = config_manager.config.replicate_api_token
        if not token:
            raise RuntimeError("REPLICATE_API_TOKEN is not configured")
        os.environ.setdefault("REPLICATE_API_TOKEN", token)
        return token

    def generate_video(
        self,
        prompt: str,
        model: str = "wan_2_1_t2v_480p",
        params: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
    ) -> MediaAsset:
        self._ensure_token()
        params = params or {}

        if _REPLICATE_UTILS_AVAILABLE:
            logger.info("Generating Replicate video via utils: model=%s", model)
            result = generate_broll_video(
                prompt=prompt,
                model_name=model,
                output_dir=str(Path(output_path).parent) if output_path else None,
                **params,
            )
            if isinstance(result, dict) and result.get("status") == "success":
                path = result.get("output_path", "")
                return MediaAsset(path=path, asset_type="video")
            raise RuntimeError(f"Replicate generation failed: {result}")

        if not _REPLICATE_SDK_AVAILABLE:
            raise RuntimeError("replicate SDK not installed: pip install replicate")

        logger.info("Generating Replicate video via SDK: model=%s", model)
        output = _replicate_sdk.run(model, input={"prompt": prompt, **params})
        url = output[0] if isinstance(output, list) else str(output)
        if output_path is None:
            import tempfile
            tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
            output_path = tmp.name
            tmp.close()
        resp = requests.get(url, timeout=120)
        resp.raise_for_status()
        Path(output_path).write_bytes(resp.content)
        logger.info("Replicate video saved: %s", output_path)
        return MediaAsset(path=output_path, asset_type="video")

    def list_models(self) -> list:
        if _REPLICATE_UTILS_AVAILABLE:
            return get_available_models()
        return []


replicate_service = ReplicateService()
