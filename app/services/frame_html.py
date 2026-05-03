"""HTML→PNG frame renderer (Playwright headless Chromium).

Adapted from Pixelle-Video's pixelle_video/services/frame_html.py
(Apache 2.0). Differences from upstream:

  - Sync wrapper (`render_sync`) for Streamlit pages.
  - Templates resolved against config_manager.template.templates_dir
    instead of cwd.
  - Browser is shared across all calls in the same process; explicit
    `close_browser()` for clean shutdown.

ReelForge use case: text-card B-Roll. When you have data, quotes, or
chapter titles that don't need photorealistic generation, render an HTML
template instead — instant, free, deterministic.

Linux deps:
    sudo apt install -y fontconfig fonts-liberation fonts-noto-cjk
    playwright install --with-deps chromium

Windows: `playwright install chromium`
"""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any, Optional

from app.core.config import config_manager
from app.core.logging import get_logger
from app.core.models import MediaAsset

logger = get_logger("services.frame_html")

_PARAM_PATTERN = re.compile(r"\{\{([a-zA-Z_][a-zA-Z0-9_]*)(?::([a-z]+))?(?:=([^}]+))?\}\}")
_PRESET_PARAMS = {"title", "text", "image", "index"}
_SIZE_PATTERN = re.compile(r"(\d+)x(\d+)")


def parse_template_size(template_path: str) -> tuple[int, int]:
    """Extract WIDTHxHEIGHT from a path like '1080x1920/image_default.html'."""
    match = _SIZE_PATTERN.search(template_path)
    if not match:
        return 1080, 1920
    return int(match.group(1)), int(match.group(2))


class HTMLFrameRenderer:
    """Singleton HTML→PNG renderer with a shared headless browser."""

    _browser = None
    _playwright = None
    _instance: Optional["HTMLFrameRenderer"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ── lifecycle ──────────────────────────────────────────────────────────

    @classmethod
    async def _ensure_browser(cls):
        if cls._browser is not None and cls._browser.is_connected():
            return cls._browser
        from playwright.async_api import async_playwright

        cls._playwright = await async_playwright().start()
        cls._browser = await cls._playwright.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu", "--disable-extensions"],
        )
        logger.info("Playwright Chromium launched")
        return cls._browser

    @classmethod
    async def close_browser(cls) -> None:
        if cls._browser:
            await cls._browser.close()
            cls._browser = None
        if cls._playwright:
            await cls._playwright.stop()
            cls._playwright = None
            logger.info("Playwright closed")

    # ── public API ──────────────────────────────────────────────────────────

    def resolve_template(self, template_path: str) -> Path:
        templates_dir = Path(config_manager.config.template.templates_dir)
        candidate = (templates_dir / template_path).resolve()
        if candidate.exists():
            return candidate
        bare = Path(template_path)
        if bare.exists():
            return bare.resolve()
        raise FileNotFoundError(f"Template not found: {template_path}")

    async def render(
        self,
        template_path: str,
        title: str = "",
        text: str = "",
        image: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
        output_path: Optional[Path] = None,
    ) -> MediaAsset:
        path = self.resolve_template(template_path)
        width, height = parse_template_size(template_path)
        html_template = path.read_text(encoding="utf-8")

        context: dict[str, Any] = {"title": title, "text": text, "image": _normalize_image(image)}
        if params:
            context.update(params)

        rendered_html = self._substitute(html_template, context)
        out = self._resolve_output_path(output_path)

        browser = await self._ensure_browser()
        page = await browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
        tmp_html: Optional[str] = None
        try:
            fd, tmp_html = tempfile.mkstemp(suffix=".html", prefix="rf_frame_")
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(rendered_html)
            await page.goto(Path(tmp_html).as_uri(), wait_until="networkidle")
            await page.screenshot(path=str(out), type="png", omit_background=True)
        finally:
            await page.close()
            if tmp_html and os.path.exists(tmp_html):
                os.unlink(tmp_html)

        logger.info(f"Frame rendered: {out} ({width}x{height})")
        return MediaAsset(
            media_type="image",
            backend="playwright",
            path=out,
            width=width,
            height=height,
            metadata={"template": template_path},
        )

    def render_sync(
        self,
        template_path: str,
        title: str = "",
        text: str = "",
        image: Optional[str] = None,
        params: Optional[dict[str, Any]] = None,
        output_path: Optional[Path] = None,
    ) -> MediaAsset:
        return asyncio.run(self.render(template_path, title, text, image, params, output_path))

    def list_templates(self, aspect: Optional[str] = None) -> list[str]:
        """Return template paths relative to the templates root.

        `aspect` filters by aspect-ratio dir (e.g., "1080x1920").
        """
        root = Path(config_manager.config.template.templates_dir)
        if not root.exists():
            return []
        target = root / aspect if aspect else root
        return sorted(str(p.relative_to(root)).replace("\\", "/") for p in target.rglob("*.html"))

    # ── helpers ────────────────────────────────────────────────────────────

    def _substitute(self, html: str, values: dict[str, Any]) -> str:
        def repl(match: re.Match) -> str:
            name = match.group(1)
            default = match.group(3)
            if name in values:
                v = values[name]
                if isinstance(v, bool):
                    return "true" if v else "false"
                return "" if v is None else str(v)
            return default if default else ""

        return _PARAM_PATTERN.sub(repl, html)

    def _resolve_output_path(self, output_path: Optional[Path]) -> Path:
        if output_path is not None:
            out = Path(output_path)
        else:
            media = Path(config_manager.storage().media_dir) / "frames"
            out = media / f"frame_{uuid.uuid4().hex[:16]}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        return out


def _normalize_image(image: Optional[str]) -> str:
    """Convert a local path to a file:// URI so the headless browser can load it."""
    if not image:
        return ""
    if image.startswith(("http://", "https://", "data:", "file://")):
        return image
    p = Path(image)
    if not p.is_absolute():
        p = (Path.cwd() / p).resolve()
    return p.as_uri() if p.exists() else image


# module-level singleton
frame_renderer = HTMLFrameRenderer()
