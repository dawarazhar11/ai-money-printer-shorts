"""Loguru bootstrap.

One configuration is set up the first time `get_logger` is called. Subsequent
calls just return a bound logger. We intentionally don't accept arguments —
configuration comes from environment variables so the same code works in
Streamlit, FastAPI, and CLI entry points.

Env vars:
  REELFORGE_LOG_LEVEL      default "INFO"  (DEBUG/INFO/WARNING/ERROR)
  REELFORGE_LOG_DIR        default "logs"
  REELFORGE_LOG_JSON       default "0"     ("1" → JSON-serialized records)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from threading import Lock

from loguru import logger

_configured = False
_lock = Lock()


def _configure() -> None:
    global _configured
    with _lock:
        if _configured:
            return

        level = os.getenv("REELFORGE_LOG_LEVEL", "INFO").upper()
        log_dir = Path(os.getenv("REELFORGE_LOG_DIR", "logs"))
        log_dir.mkdir(parents=True, exist_ok=True)
        json_logs = os.getenv("REELFORGE_LOG_JSON", "0") == "1"

        logger.remove()

        console_format = (
            "<green>{time:HH:mm:ss}</green> "
            "<level>{level:<7}</level> "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stderr,
            level=level,
            format=console_format,
            colorize=True,
            backtrace=True,
            diagnose=False,
        )

        logger.add(
            log_dir / "reelforge.log",
            level=level,
            rotation="20 MB",
            retention="14 days",
            compression="zip",
            serialize=json_logs,
            enqueue=True,
            backtrace=True,
            diagnose=False,
        )

        _configured = True


def get_logger(name: str):
    """Return a logger bound to `name`. Safe to call from anywhere."""
    if not _configured:
        _configure()
    return logger.bind(component=name)
