"""
Core/config/logging_config.py

Centralized logging configuration cho Mr.Holmes.

Story 4.3 — Logging Module Migration: print() → logging, Epic 4.

Design:
    - Logger hierarchy: root logger "mrholmes" với ChildLoggers per module.
    - Console handler: stderr (không pollute stdout OSINT output).
    - File handler: optional, writes to logs/mrholmes.log.
    - Log levels mapped từ CLI print patterns:
        [!] RED   → logger.warning() / logger.error()
        [v] YELLOW→ logger.info()    (FOUND result)
        [I] BLUE  → logger.debug()   (info/status)
        [N] BLUE  → logger.warning() (connection issue)
        [+] GREEN → logger.info()    (progress/setup)

Usage:
    from Core.config.logging_config import get_logger
    logger = get_logger(__name__)

    logger.info("Site found: %s", url)
    logger.warning("Connection issue: %s", site)
    logger.error("Request failed: %s", exc)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ROOT_LOGGER_NAME = "mrholmes"
_LOG_DIR = Path(__file__).resolve().parent.parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "mrholmes.log"

_DEFAULT_FORMAT = "[%(levelname)s] %(name)s: %(message)s"
_FILE_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ---------------------------------------------------------------------------
# Internal: setup called once
# ---------------------------------------------------------------------------

_configured = False


def setup_logging(
    level: int = logging.WARNING,
    enable_file: bool = False,
) -> None:
    """
    Configure the root 'mrholmes' logger.

    Args:
        level:       Minimum log level to show on console. Default: WARNING
                     (quiet by default — similar to original print behaviour).
        enable_file: If True, also write DEBUG+ to logs/mrholmes.log.

    This function is idempotent — calling it multiple times is safe.
    """
    global _configured

    root = logging.getLogger(_ROOT_LOGGER_NAME)

    # Prevent duplicate handlers if called multiple times
    if root.handlers:
        return

    root.setLevel(logging.DEBUG)  # Capture all, handlers filter

    # Console handler (stderr) — respect 'level' argument
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter(_DEFAULT_FORMAT))
    root.addHandler(console_handler)

    # File handler — optional (AC4)
    if enable_file:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(_LOG_FILE), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_DATE_FORMAT))
        root.addHandler(file_handler)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger scoped under the 'mrholmes' hierarchy.

    Usage in each module (AC5):
        from Core.config.logging_config import get_logger
        logger = get_logger(__name__)

    Args:
        name: Typically __name__ of the calling module.
              If name already starts with 'mrholmes', uses as-is.
              Otherwise, prepends 'mrholmes.' prefix.
    """
    if not _configured:
        # Auto-configure with sensible defaults if setup_logging() not called explicitly
        _auto_setup()

    if name.startswith(_ROOT_LOGGER_NAME):
        return logging.getLogger(name)
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")


def _auto_setup() -> None:
    """Auto-configure from environment variables if explicit setup not called."""
    level_name = os.environ.get("MH_LOG_LEVEL", "WARNING").upper()
    level = getattr(logging, level_name, logging.WARNING)
    enable_file = os.environ.get("MH_LOG_FILE", "false").lower() == "true"
    setup_logging(level=level, enable_file=enable_file)
