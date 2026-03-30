"""
Core/plugins/leak_lookup.py

Story 7.5 — Leak-Lookup API Integration
A free alternative to HaveIBeenPwned for breach lookups.
"""
from __future__ import annotations

import asyncio
import time

import aiohttp

from Core.plugins.base import IntelligencePlugin, PluginResult


class LeakLookupPlugin(IntelligencePlugin):
    """
    Intelligence plugin interfacing with Leak-Lookup.com.
    """

    # Class-level lock and rate limiting tracker (1 request per second)
    _lock = asyncio.Lock()
    _last_request_time = 0.0
    _rate_limit_delay = 1.0

    def __init__(self, api_key: str = "") -> None:
        self.api_key = api_key

    # API Constants
    BASE_URL = "https://leak-lookup.com/api/search"
    SUPPORTED_TYPES = {
        "EMAIL": "email_address",
        "IP": "ipaddress",
        "USERNAME": "username",
        "DOMAIN": "domain",
    }

    @property
    def name(self) -> str:
        return "LeakLookup"

    @property
    def requires_api_key(self) -> bool:
        return True

    async def check(self, target: str, target_type: str) -> PluginResult:
        """
        Query Leak-Lookup for the given target.
        """
        # Validate target type
        target_type_upper = target_type.upper()
        if target_type_upper not in self.SUPPORTED_TYPES:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"{self.name} only supports {', '.join(self.SUPPORTED_TYPES.keys())}.",
            )

        if not self.api_key:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"{self.name} API Key missing. Please configure MH_LEAKLOOKUP_API_KEY.",
            )

        # Enforce Rate Limiting
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_time
            if elapsed < self._rate_limit_delay:
                wait_time = self._rate_limit_delay - elapsed
                await asyncio.sleep(wait_time)
            self.__class__._last_request_time = time.monotonic()

        # Prepare HTTP Request
        payload = {
            "key": self.api_key,
            "type": self.SUPPORTED_TYPES[target_type_upper],
            "query": target,
        }

        # Issue network call
        try:
            # Using ephemeral local session to comply with IntelligencePlugin decoupled constraint
            # (Deferred Epic-wide Session Pool: Review Record 7.3)
            async with aiohttp.ClientSession() as session:
                async with session.post(self.BASE_URL, data=payload, timeout=10) as response:
                    
                    if response.status == 429:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="429 Too Many Requests - Rate limit exceeded.",
                        )
                    
                    if response.status != 200:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"HTTP {response.status}",
                        )
                        
                    data = await response.json()
                    
                    # Leak Lookup specific error handling inside JSON 
                    # {"error": "true", "message": "Invalid API Key"}
                    if str(data.get("error", "")).lower() == "true":
                        msg = data.get("message", "Unknown API error")
                        if "invalid api key" in str(msg).lower():
                            msg = f"401 Unauthorized - {msg}"
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=msg,
                        )

                    # Extract the payload which is located in "message"
                    # {"error": "false", "message": {"database_name1": ["data"], "database_name2": ["data"]}}
                    leak_dict = data.get("message", {})
                    
                    # If message is a list or empty string instead of dict (e.g. no results found)
                    if not isinstance(leak_dict, dict):
                        leak_dict = {}

                    db_names = list(leak_dict.keys())

                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": len(db_names) > 0,
                            "vulnerabilities": db_names,
                            "metadata": {
                                "total_breaches": len(db_names)
                            }
                        },
                    )

        except asyncio.TimeoutError:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Request timed out",
            )
        except aiohttp.ClientError as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Network error: {str(e)}",
            )
        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Unexpected error: {str(e)}",
            )
