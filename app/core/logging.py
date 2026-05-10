"""Loguru wrapper for ReelForge."""
import sys
from loguru import logger as _root_logger

_configured = False


def get_logger(name: str):
    """Return a loguru logger bound to the given name."""
    global _configured
    if not _configured:
        _root_logger.remove()
        _root_logger.add(
            sys.stderr,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[name]}</cyan> — {message}",
            level="DEBUG",
        )
        _configured = True
    return _root_logger.bind(name=name)
