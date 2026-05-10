import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.frame_html")

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "frames"


class FrameRenderer:
    """Render static HTML frame templates into image/video MediaAssets."""

    def list_templates(self) -> List[str]:
        if not _TEMPLATES_DIR.exists():
            return []
        return sorted(p.stem for p in _TEMPLATES_DIR.glob("*.html"))

    def render_sync(
        self,
        template_path: str,
        title: str = "",
        text: str = "",
        image: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
        output_path: Optional[str] = None,
    ) -> MediaAsset:
        params = params or {}
        tpath = Path(template_path)
        if not tpath.exists():
            raise FileNotFoundError(f"Frame template not found: {template_path}")

        html = tpath.read_text(encoding="utf-8")
        html = html.replace("{{TITLE}}", title)
        html = html.replace("{{TEXT}}", text)
        if image:
            html = html.replace("{{IMAGE}}", image)
        for k, v in params.items():
            html = html.replace(f"{{{{{k}}}}}", str(v))

        if output_path is None:
            tmp = tempfile.NamedTemporaryFile(suffix=".html", delete=False)
            output_path = tmp.name
            tmp.close()

        Path(output_path).write_text(html, encoding="utf-8")
        logger.info("Frame rendered: %s -> %s", tpath.name, output_path)
        return MediaAsset(path=output_path, asset_type="html")


frame_renderer = FrameRenderer()
