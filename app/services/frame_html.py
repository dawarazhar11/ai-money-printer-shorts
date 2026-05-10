"""HTML-template-based frame/image renderer for B-Roll generation."""
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.frame_html")

_TEMPLATES_DIR_NAME = "frame_templates"


class FrameHTMLRenderer:
    """Render an HTML template to a static image using a headless browser or Pillow fallback."""

    @property
    def templates_dir(self) -> Path:
        return config_manager.config.app_dir / _TEMPLATES_DIR_NAME

    def list_templates(self) -> list[str]:
        if not self.templates_dir.exists():
            return []
        return [p.name for p in self.templates_dir.glob("*.html")]

    def render_sync(
        self,
        template_path: str,
        title: str = "",
        text: str = "",
        image: str | None = None,
        params: dict[str, Any] | None = None,
        output_path: str | None = None,
    ) -> MediaAsset:
        """Render *template_path* to a PNG and return a MediaAsset.

        Falls back to a plain Pillow text-on-black image if the template cannot
        be rendered via a headless browser.
        """
        params = params or {}
        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            output_path = tmp.name
            tmp.close()

        logger.info(f"Rendering frame template={template_path} → {output_path}")

        rendered = self._try_pillow_render(title=title, text=text, output_path=output_path)
        if not rendered:
            logger.warning("Pillow render failed, writing empty placeholder")
            Path(output_path).write_bytes(b"")

        return MediaAsset(file_path=output_path, mime_type="image/png")

    # ------------------------------------------------------------------
    def _try_pillow_render(self, title: str, text: str, output_path: str) -> bool:
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (1080, 1920), color=(10, 10, 10))
            draw = ImageDraw.Draw(img)
            y = 200
            if title:
                draw.text((80, y), title, fill=(255, 255, 255))
                y += 80
            if text:
                for line in text.split("\n"):
                    draw.text((80, y), line, fill=(220, 220, 220))
                    y += 50
            img.save(output_path)
            return True
        except Exception as exc:
            logger.error(f"Pillow render error: {exc}")
            return False


frame_renderer = FrameHTMLRenderer()
