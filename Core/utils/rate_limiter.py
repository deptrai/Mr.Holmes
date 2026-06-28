"""
Core/utils/rate_limiter.py — AD-12: Centralized Rate Limiter

Coordinates rate limiting across plugins to prevent IP bans on government
portals and other sensitive sources.

Usage::

    from Core.utils.rate_limiter import RateLimiter

    limiter = RateLimiter.get_instance()
    await limiter.wait_if_needed("tracuunnt.gdt.gov.vn", "VnTax")
    # ... make request ...
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict
from urllib.parse import urlparse


class RateLimiter:
    """Centralized rate limiter with per-domain and per-plugin limits.

    Uses a singleton pattern so all plugins share the same limiter instance.
    """

    _instance: "RateLimiter | None" = None
    _lock = asyncio.Lock()

    # Default rate limits (seconds between requests)
    _DEFAULT_DOMAIN_LIMITS: dict[str, float] = {
        "tracuunnt.gdt.gov.vn": 3.0,       # Vietnam tax portal
        "thuvienphapluat.vn": 5.0,         # Vietnam legal library
        "dangkykinhdoanh.gov.vn": 3.0,     # Vietnam business registry
        "zalo.me": 2.0,                    # Zalo
        "mbasic.facebook.com": 2.0,        # Facebook basic
        "instagram.com": 2.0,              # Instagram
        "tiktok.com": 2.0,                 # TikTok
        "linkedin.com": 5.0,               # LinkedIn (stricter)
        "api.xinvoice.vn": 1.0,            # XInvoice API
        "api.truecaller.com": 2.0,         # Truecaller API
        "snusbase.com": 1.0,               # Snusbase API
    }

    _DEFAULT_PLUGIN_LIMITS: dict[str, float] = {
        "VnTax": 3.0,
        "VnCourt": 5.0,
        "VnNews": 2.0,
        "Zalo": 2.0,
        "FacebookVn": 2.0,
        "Instagram": 2.0,
        "TikTokVn": 2.0,
        "LinkedIn": 5.0,
    }

    def __init__(self) -> None:
        self._domain_limits: dict[str, float] = dict(self._DEFAULT_DOMAIN_LIMITS)
        self._plugin_limits: dict[str, float] = dict(self._DEFAULT_PLUGIN_LIMITS)
        self._last_request: dict[str, float] = defaultdict(float)
        self._locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    @classmethod
    def get_instance(cls) -> "RateLimiter":
        """Get or create the singleton RateLimiter instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_domain_limit(self, domain: str, min_interval: float) -> None:
        """Override rate limit for a specific domain."""
        self._domain_limits[domain] = min_interval

    def set_plugin_limit(self, plugin: str, min_interval: float) -> None:
        """Override rate limit for a specific plugin."""
        self._plugin_limits[plugin] = min_interval

    def _extract_domain(self, url_or_domain: str) -> str:
        """Extract domain from URL or return as-is if already a domain."""
        if "://" in url_or_domain:
            parsed = urlparse(url_or_domain)
            return parsed.netloc or parsed.path
        return url_or_domain

    def _get_limit(self, domain: str, plugin: str) -> float:
        """Get the effective rate limit (max of domain and plugin limits)."""
        domain_limit = self._domain_limits.get(domain, 0.0)
        plugin_limit = self._plugin_limits.get(plugin, 0.0)
        return max(domain_limit, plugin_limit)

    async def wait_if_needed(self, url_or_domain: str, plugin: str = "") -> None:
        """Wait if rate limit requires it before making a request.

        Args:
            url_or_domain: URL or domain to check rate limit for
            plugin: Plugin name making the request
        """
        domain = self._extract_domain(url_or_domain)
        limit = self._get_limit(domain, plugin)

        if limit <= 0:
            return

        # Use per-domain lock to serialize requests to same domain
        lock_key = domain
        async with self._locks[lock_key]:
            last = self._last_request.get(domain, 0.0)
            now = time.monotonic()
            elapsed = now - last
            if elapsed < limit:
                wait_time = limit - elapsed
                await asyncio.sleep(wait_time)
            self._last_request[domain] = time.monotonic()

    def can_request(self, domain: str, plugin: str = "") -> bool:
        """Check if a request can be made without waiting (non-blocking check)."""
        domain = self._extract_domain(domain)
        limit = self._get_limit(domain, plugin)
        if limit <= 0:
            return True
        last = self._last_request.get(domain, 0.0)
        elapsed = time.monotonic() - last
        return elapsed >= limit
