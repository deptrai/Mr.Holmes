"""
Core/config/__init__.py

Re-export Settings for convenient import:
    from Core.config import settings
    from Core.config import Settings
"""
from Core.config.settings import Settings, settings

__all__ = ["Settings", "settings"]
