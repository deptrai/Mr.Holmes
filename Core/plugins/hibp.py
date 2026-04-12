"""
Core/plugins/hibp.py

HaveIBeenPwned Intelligence Plugin integration.
"""
from __future__ import annotations

import asyncio
import time
import aiohttp
from typing import Any

from Core.plugins.base import IntelligencePlugin, PluginResult, get_http_session


class HIBPPlugin(IntelligencePlugin):
    """
    HaveIBeenPwned Intelligence Plugin.
    Requires an API key ($3.50/month).
    Rate limit constraint: 1 request per 1.5 seconds.
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
        return "HaveIBeenPwned"

    @property
    def requires_api_key(self) -> bool:
        return True

    async def check(self, target: str, target_type: str) -> PluginResult:
        if target_type.upper() != "EMAIL":
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"HIBP only supports EMAIL targets, got {target_type}",
            )

        if not self.api_key:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="HaveIBeenPwned API Key missing. Please configure MH_HAVEIBEENPWNED_API_KEY.",
            )

        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{target}"
        headers = {
            "hibp-api-key": self.api_key,
            "user-agent": "MrHolmes-OSINT",
        }

        # Enforce rate limiting: 1 req per 1.5 seconds globally
        lock = self.get_lock()
        async with lock:
            now = time.monotonic()
            elapsed = now - self.__class__._last_request_time
            wait_time = 1.5 - elapsed
            if wait_time > 0:
                await asyncio.sleep(wait_time)

            # Update timestamp right before making request, still under lock
            self.__class__._last_request_time = time.monotonic()
            
        # Outside lock - perform I/O
        try:
            async with get_http_session(self) as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 404:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "breach_count": 0,
                                "breach_names": [],
                                "breach_dates": [],
                                "data_classes": [],
                            },
                        )

                    if response.status == 401:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="401 Unauthorized - Invalid HaveIBeenPwned API key.",
                        )

                    if response.status == 429:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="429 Rate Limit Exceeded for HaveIBeenPwned.",
                        )

                    response.raise_for_status()
                    breaches = await response.json()

                    # Parse breach data as per AC3
                    breach_count = len(breaches)
                    breach_names = [b.get("Name", "") for b in breaches]
                    breach_dates = [b.get("BreachDate", "") for b in breaches]
                    
                    data_classes = set()
                    for b in breaches:
                        data_classes.update(b.get("DataClasses", []))

                    data = {
                        "breach_count": breach_count,
                        "breach_names": list(breach_names),
                        "breach_dates": list(breach_dates),
                        "data_classes": sorted(list(data_classes)),
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
                error_message=f"HIBP Network/Parse Error: {str(e)}",
            )
