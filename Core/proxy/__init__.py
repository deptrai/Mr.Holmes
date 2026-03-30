"""
Core/proxy/__init__.py

Package entrypoint — exposes ProxyManager.

Story 1.5 — Extract ProxyManager Class, Epic 1.
"""
from Core.proxy.manager import ProxyManager

__all__ = ["ProxyManager"]
