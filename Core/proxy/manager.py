"""
Core/proxy/manager.py

ProxyManager — centralizes proxy configuration and ip-api.com identity lookup.

Replaces 8 occurrences of copy-paste proxy init across:
  - Core/Searcher.py
  - Core/Searcher_phone.py
  - Core/Searcher_website.py
  - Core/Searcher_person.py
  - Core/engine/scan_pipeline.py (_resolve_proxy_identity)

Story 1.5 — Extract ProxyManager Class, Epic 1.
Foundation for Epic 3 (auto-rotate, health-check).
"""
from __future__ import annotations

import json
import urllib.request
from typing import Optional

from Core.Support import Language

filename = Language.Translation.Get_Language()

_IP_API_BASE = "http://ip-api.com/json/"


class ProxyManager:
    """
    Encapsulates proxy configuration, identity resolution, and reset.

    Usage (replaces inline pattern):
        pm = ProxyManager()
        pm.configure(choice)               # choice=1 → enable, else None
        proxy_dict = pm.get_proxy()        # {http, https} or None
        identity   = pm.get_identity()     # "Region, Country" or None

    AC3 methods: configure(), get_proxy(), get_identity(), reset()
    AC4: ip-api.com lookup centralized here
    """

    def __init__(self) -> None:
        self._proxy_dict: Optional[dict] = None
        self._proxy_ip: str = "None"
        self._identity: Optional[str] = None
        self._enabled: bool = False

    # ------------------------------------------------------------------
    # configure() — AC3
    # ------------------------------------------------------------------
    def configure(self, choice: int) -> None:
        """
        Set up proxy based on user choice.

        Args:
            choice: 1 = use proxy from config; anything else = no proxy.
        """
        if choice == 1:
            from Core.Support import Proxies
            self._proxy_dict = Proxies.proxy.final_proxis
            self._proxy_ip = Proxies.proxy.choice3
            self._enabled = True
            self._identity = self._resolve_identity()
        else:
            self._proxy_dict = None
            self._proxy_ip = "None"
            self._enabled = False
            self._identity = None

    # ------------------------------------------------------------------
    # get_proxy() — AC3
    # ------------------------------------------------------------------
    def get_proxy(self) -> Optional[dict]:
        """Return proxy dict {http, https} or None if proxy not enabled."""
        return self._proxy_dict

    # ------------------------------------------------------------------
    # get_identity() — AC3 / AC4
    # ------------------------------------------------------------------
    def get_identity(self) -> Optional[str]:
        """
        Return the geo-identity string for the current proxy, or None.

        Resolved once during configure(); cached thereafter.
        """
        return self._identity

    @property
    def proxy_ip(self) -> str:
        """Return the raw proxy IP string (e.g. '192.168.1.1') or 'None'."""
        return self._proxy_ip

    # ------------------------------------------------------------------
    # reset() — AC3
    # ------------------------------------------------------------------
    def reset(self) -> None:
        """
        Disable proxy (fallback scenario — retry without proxy).

        After reset(), get_proxy() returns None.
        get_identity() still returns the cached identity string.
        """
        self._proxy_dict = None
        self._enabled = False

    # ------------------------------------------------------------------
    # is_enabled() — convenience
    # ------------------------------------------------------------------
    def is_enabled(self) -> bool:
        """Return True if proxy is currently active."""
        return self._enabled

    # ------------------------------------------------------------------
    # ip-api.com lookup — AC4
    # ------------------------------------------------------------------
    def _resolve_identity(self) -> Optional[str]:
        """
        Query ip-api.com to get geo-location of the current proxy IP.

        Returns formatted identity string, or None on any failure.
        """
        if self._proxy_ip == "None":
            return None
        try:
            url = _IP_API_BASE + self._proxy_ip
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
            region = data.get("regionName", "Unknown")
            country = data.get("country", "Unknown")
            return Language.Translation.Translate_Language(
                filename, "Default", "ProxyLoc", "None").format(region, country)
        except (OSError, json.JSONDecodeError, KeyError, ValueError):
            return None
