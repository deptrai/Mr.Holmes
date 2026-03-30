"""
Core/plugins/searxng.py

Story 7.6 — SearxNG OSINT Integration
Uses SearxNG JSON format to bypass captchas and perform dork queries.
"""
from __future__ import annotations

import asyncio
import os

import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult


class SearxngPlugin(IntelligencePlugin):
    """
    Intelligence plugin interfacing with a SearxNG instance.
    Uses 'MH_SEARXNG_URL' environment variable or defaults to a public instance.
    """

    SUPPORTED_TYPES = {"EMAIL", "USERNAME", "IP", "DOMAIN"}

    def __init__(self, api_key: str = "") -> None:
        """SearxNG public JSON APIs do not strictly require an API key by default."""
        self.api_key = api_key
        # Check environment for custom instance
        custom_url = os.environ.get("MH_SEARXNG_URL", "").strip()
        self.base_url = custom_url if custom_url else "https://searx.be/search"

    @property
    def name(self) -> str:
        return "SearxngOSINT"

    @property
    def requires_api_key(self) -> bool:
        """Does not require api key to operate."""
        return False

    def _build_query(self, target: str, target_type: str) -> str:
        """Creates the dorking query based on user target type."""
        # A simple base query looking for leaks, passwords or dumps
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
        # Validate target type
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

        try:
            # Using ephemeral local session to comply with IntelligencePlugin decoupled constraint
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params, timeout=15) as response:
                    if response.status == 429:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"429 Too Many Requests - SearxNG node rate limit. Switch MH_SEARXNG_URL.",
                        )
                    
                    if response.status != 200:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"HTTP {response.status}",
                        )
                        
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
                                "searxng_node": self.base_url,
                                "total_clues": len(osint_urls),
                                "query_used": query
                            }
                        },
                    )

        except asyncio.TimeoutError:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Request timed out. SearxNG node might be down.",
            )
        except aiohttp.ClientError as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Network error: {str(e)}. Consider changing MH_SEARXNG_URL.",
            )
        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Unexpected error: {str(e)}",
            )
