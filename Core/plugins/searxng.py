"""
Core/plugins/searxng.py

Story 7.6 — SearxNG OSINT Integration
Uses SearxNG JSON format to bypass captchas and perform dork queries.

Update: Implemented random node rotation, User-Agent rotation, delay between
retries, DuckDuckGo fallback, and custom-URL-to-public-node fallthrough.
"""
from __future__ import annotations

import asyncio
import os
import random

import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult, get_http_session


# Diverse User-Agent pool to reduce fingerprinting-based blocks
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:126.0) Gecko/20100101 Firefox/126.0",
]


class SearxngPlugin(IntelligencePlugin):
    """
    Intelligence plugin interfacing with a SearxNG instance.
    Uses 'MH_SEARXNG_URL' environment variable or defaults to a public instance pool.
    """

    SUPPORTED_TYPES = {"EMAIL", "USERNAME", "IP", "DOMAIN"}

    # Expanded pool of public nodes — more nodes = higher chance of success.
    # Last verified: 2026-04-05.
    FALLBACK_NODES = [
        "https://search.inetol.net/search",
        "https://search.ononoki.org/search",
        "https://paulgo.io/search",
        "https://searx.tiekoetter.com/search",
        "https://priv.au/search",
        "https://search.mdosch.de/search",
        "https://searx.be/search",
        "https://opnxng.com/search",
        "https://etsi.me/search",
        "https://search.sapti.me/search",
        "https://search.rhscz.eu/search",
        "https://searx.namejeff.xyz/search",
    ]

    # How many public nodes to try before giving up
    _MAX_PUBLIC_TRIES = 5

    def __init__(self, api_key: str = "") -> None:
        """SearxNG public JSON APIs do not strictly require an API key by default."""
        self.api_key = api_key
        self.custom_url = os.environ.get("MH_SEARXNG_URL", "").strip()

    @property
    def name(self) -> str:
        return "SearxngOSINT"

    @property
    def requires_api_key(self) -> bool:
        return False

    def _build_query(self, target: str, target_type: str) -> str:
        """Creates the dorking query based on user target type."""
        safe_target = f'"{target}"'
        if target_type in ("EMAIL", "USERNAME"):
            return f"{safe_target} password OR leak OR dump"
        elif target_type in ("IP", "DOMAIN"):
            return f"{safe_target} vulnerability OR exploit OR CVE"
        return safe_target

    async def check(self, target: str, target_type: str) -> PluginResult:
        """Query SearxNG for the given target via a JSON call."""
        target_type_upper = target_type.upper()
        if target_type_upper not in self.SUPPORTED_TYPES:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"{self.name} only supports {', '.join(sorted(self.SUPPORTED_TYPES))}.",
            )

        query = self._build_query(target, target_type_upper)
        params = {"q": query, "format": "json", "language": "all", "pageno": 1}

        # Build URL list: custom URL first (if set), then random public nodes
        public_nodes = random.sample(
            self.FALLBACK_NODES, min(self._MAX_PUBLIC_TRIES, len(self.FALLBACK_NODES))
        )
        urls_to_try = ([self.custom_url] + public_nodes) if self.custom_url else public_nodes
        last_error = "All nodes failed."

        for i, base_url in enumerate(urls_to_try):
            # Small delay between retries to avoid triggering rate limits
            if i > 0:
                await asyncio.sleep(0.5 + random.random())

            headers = {
                "User-Agent": random.choice(_USER_AGENTS),
                "Accept": "application/json",
            }

            try:
                async with get_http_session(self) as session:
                    async with session.get(
                        base_url, params=params, headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as response:
                        if response.status == 429:
                            last_error = f"HTTP 429 (Rate limit) at {base_url}"
                            continue
                        if response.status == 403:
                            last_error = f"HTTP 403 (Blocked/Captcha) at {base_url}"
                            continue
                        if response.status != 200:
                            last_error = f"HTTP {response.status} at {base_url}"
                            continue

                        data = await response.json()
                        results = data.get("results") or []
                        osint_urls = [
                            {"url": item["url"], "title": item.get("title", "Unknown Title")}
                            for item in results if item.get("url")
                        ]

                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "data_found": len(osint_urls) > 0,
                                "osint_urls": osint_urls,
                                "metadata": {
                                    "searxng_node": base_url,
                                    "total_clues": len(osint_urls),
                                    "query_used": query,
                                },
                            },
                        )

            except asyncio.TimeoutError:
                last_error = f"Timeout at {base_url}"
                continue
            except aiohttp.ClientError as e:
                last_error = f"Network error at {base_url}: {e}"
                continue
            except Exception as e:
                last_error = f"Unexpected error at {base_url}: {e}"
                continue

        # All SearxNG nodes failed — try DuckDuckGo as final fallback
        try:
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=10))
                if ddg_results:
                    osint_urls = [
                        {"url": r["href"], "title": r.get("title", "Unknown")}
                        for r in ddg_results if r.get("href")
                    ]
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": len(osint_urls) > 0,
                            "osint_urls": osint_urls,
                            "metadata": {
                                "searxng_node": "duckduckgo-fallback",
                                "total_clues": len(osint_urls),
                                "query_used": query,
                            },
                        },
                    )
        except Exception:
            pass  # DDG fallback failed too

        # Exhausted all attempts
        return PluginResult(
            plugin_name=self.name,
            is_success=False,
            data={},
            error_message=f"SearxNG Nodes exhausted. Last error: {last_error}. Consider setting working MH_SEARXNG_URL.",
        )
