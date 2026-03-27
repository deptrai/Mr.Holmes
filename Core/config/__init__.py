"""
Core/config/__init__.py

Re-export Settings and logging utilities for convenient import:
    from Core.config import settings
    from Core.config import Settings
    from Core.config import get_logger
"""
from Core.config.settings import Settings, settings
from Core.config.logging_config import get_logger, setup_logging

__all__ = ["Settings", "settings", "get_logger", "setup_logging"]

