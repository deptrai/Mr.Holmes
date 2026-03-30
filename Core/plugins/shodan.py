"""
Core/plugins/shodan.py

Story 7.3 — Shodan Intelligence Plugin integration.
"""
from __future__ import annotations

import asyncio
import time
import aiohttp
from typing import Any

from Core.plugins.base import IntelligencePlugin, PluginResult


class ShodanPlugin(IntelligencePlugin):
    """
    Shodan Intelligence Plugin.
    Requires an API key. 
    Rate limit constraint: 1 request per 1 second.
    API: /shodan/host/{ip}
    """

    _last_request_time: float = 0.0
    _lock: asyncio.Lock | None = None

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    @classmethod
    def get_lock(cls) -> asyncio.Lock:
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        return cls._lock

    @property
    def name(self) -> str:
        return "Shodan"

    @property
    def requires_api_key(self) -> bool:
        return True

    async def check(self, target: str, target_type: str) -> PluginResult:
        if target_type.upper() != "IP":
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Shodan only supports IP targets, got {target_type}",
            )

        if not self.api_key:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Shodan API Key missing. Please configure MH_SHODAN_API_KEY.",
            )

        url = f"https://api.shodan.io/shodan/host/{target}?key={self.api_key}"

        # Enforce rate limiting: 1 req per 1 second globally
        lock = self.get_lock()
        async with lock:
            now = time.monotonic()
            elapsed = now - self.__class__._last_request_time
            wait_time = 1.0 - elapsed
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            # Update timestamp right before making request
            self.__class__._last_request_time = time.monotonic()

        # Outside lock - perform I/O
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=10) as response:
                    if response.status == 404:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "data_found": False,
                                "ports": [],
                                "hostnames": [],
                                "org": "n/a",
                                "isp": "n/a",
                                "vulnerabilities": [],
                            },
                        )

                    if response.status == 401:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="401 Unauthorized - Invalid Shodan API key.",
                        )

                    if response.status == 429:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="429 Rate Limit Exceeded for Shodan.",
                        )

                    response.raise_for_status()
                    host_data = await response.json()

                    # Parse data per AC
                    ports = host_data.get("ports", [])
                    hostnames = host_data.get("hostnames", [])
                    org = host_data.get("org", "n/a")
                    isp = host_data.get("isp", "n/a")
                    
                    # Extract vulnerabilities (CVEs) from banners
                    vulnerabilities = []
                    for item in host_data.get("data", []):
                        vulns = item.get("vulns", [])
                        if vulns:
                            # vulns is often a list or a dict in older banners
                            if isinstance(vulns, list):
                                vulnerabilities.extend(vulns)
                            elif isinstance(vulns, dict):
                                vulnerabilities.extend(vulns.keys())
                    
                    # Deduplicate CVEs
                    vulnerabilities = sorted(list(set(vulnerabilities)))

                    data = {
                        "data_found": True,
                        "ports": ports,
                        "hostnames": hostnames,
                        "org": org,
                        "isp": isp,
                        "vulnerabilities": vulnerabilities,
                        "location": {
                            "city": host_data.get("city"),
                            "country": host_data.get("country_name"),
                            "os": host_data.get("os"),
                        }
                    }

                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data=data,
                    )

        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Shodan Network/Parse Error: {str(e)}",
            )
