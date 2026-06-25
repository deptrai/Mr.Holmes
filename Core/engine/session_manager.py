"""
Core/engine/session_manager.py

Modern session manager — extracted from legacy Core/Session.py.
Exposes the current user agent and proxy as data without interactive
prompts or process restarts.

Phase-out Phase 1 — SessionManager replaces Core.Session.Options.
"""
from __future__ import annotations

import os
from typing import Optional

from Core.Support import Useragent
from Core.Support import Proxies

_logger = None


def _logger():
    """Lazy logger để tránh module-level I/O side effects."""
    global _logger
    if _logger is None:
        from Core.config.logging_config import get_logger
        _logger = get_logger(__name__)
    return _logger


class SessionManager:
    """
    Session management utilities.

    Replaces legacy Core.Session.Options.
    """

    @staticmethod
    def get_useragent() -> str:
        """Get current user agent string.

        Returns:
            The currently selected user agent string.
        """
        return Useragent.Select.agent

    @staticmethod
    def get_proxy() -> str:
        """Get current proxy IP.

        Returns:
            The currently selected proxy IP string.
        """
        return Proxies.proxy.choice3

    @staticmethod
    def display_session_info() -> dict:
        """Return session info as dict.

        Returns:
            Dict with keys ``useragent`` and ``proxy``.
        """
        return {
            "useragent": SessionManager.get_useragent(),
            "proxy": SessionManager.get_proxy(),
        }
