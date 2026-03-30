"""
Core/plugins/searxng.py

Story 7.6 — SearxNG OSINT Integration
Uses SearxNG JSON format to bypass captchas and perform dork queries.

Update: Implemented random node rotation and robust User-Agent to bypass HTTP 403 / 429 errors from public instances.
"""
from __future__ import annotations

import asyncio
import os
import random

import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult


class SearxngPlugin(IntelligencePlugin):
    """
    Intelligence plugin interfacing with a SearxNG instance.
    Uses 'MH_SEARXNG_URL' environment variable or defaults to a public instance pool.
    """

    SUPPORTED_TYPES = {"EMAIL", "USERNAME", "IP", "DOMAIN"}
    
    # Pool of public nodes — verified working ones listed first, rest as fallback.
    # Last verified: 2026-03-31. Swap if nodes rotate offline.
    FALLBACK_NODES = [
        "https://search.inetol.net/search",   # verified 200 OK
        "https://search.ononoki.org/search",
        "https://paulgo.io/search",
        "https://searx.tiekoetter.com/search",
        "https://priv.au/search",
        "https://search.mdosch.de/search",
        "https://searx.be/search",
    ]

    def __init__(self, api_key: str = "") -> None:
        """SearxNG public JSON APIs do not strictly require an API key by default."""
        self.api_key = api_key
        # Check environment for custom instance
        self.custom_url = os.environ.get("MH_SEARXNG_URL", "").strip()

    @property
    def name(self) -> str:
        return "SearxngOSINT"

    @property
    def requires_api_key(self) -> bool:
        """Does not require api key to operate."""
        return False

    def _build_query(self, target: str, target_type: str) -> str:
        """Creates the dorking query based on user target type."""
        safe_target = f'"{target}"'
        if target_type == "EMAIL" or target_type == "USERNAME":
            return f"{safe_target} password OR leak OR dump"
        elif target_type == "IP" or target_type == "DOMAIN":
            return f"{safe_target} vulnerability OR exploit OR CVE"
        return safe_target

    async def check(self, target: str, target_type: str) -> PluginResult:
        """
        Query SearxNG for the given target via a JSON call.
        """
        target_type_upper = target_type.upper()
        if target_type_upper not in self.SUPPORTED_TYPES:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"{self.name} only supports {', '.join(sorted(self.SUPPORTED_TYPES))}.",
            )

        query = self._build_query(target, target_type_upper)

        params = {
            "q": query,
            "format": "json",
            "engines": "google,duckduckgo,bing",
            "language": "en"
        }
        
        headers = {
            # Realistic User-Agent defeats many basic WAF/Anti-Bot checks (e.g. Cloudflare, searx.be JS challenge)
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }

        # Try user-configured node first. If not set, try up to 3 random public nodes to bypass 429/403.
        urls_to_try = [self.custom_url] if self.custom_url else random.sample(self.FALLBACK_NODES, min(3, len(self.FALLBACK_NODES)))
        last_error = "All nodes failed."

        for base_url in urls_to_try:
            try:
                # Using ephemeral local session to comply with plugin isolated scope
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(base_url, params=params, timeout=15) as response:
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
                        osint_urls = []
                        for item in results:
                            url = item.get("url")
                            title = item.get("title", "Unknown Title")
                            if url:
                                osint_urls.append({"url": url, "title": title})

                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "data_found": len(osint_urls) > 0,
                                "osint_urls": osint_urls,
                                "metadata": {
                                    "searxng_node": base_url,
                                    "total_clues": len(osint_urls),
                                    "query_used": query
                                }
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
                
        # Exhausted all attempts
        return PluginResult(
            plugin_name=self.name,
            is_success=False,
            data={},
            error_message=f"SearxNG Nodes exhausted. Last error: {last_error}. Consider setting working MH_SEARXNG_URL.",
        )
