"""Core/plugins/snusbase.py — Snusbase breach database search.

Snusbase is a paid breach database search engine.
Searches by email, username, phone, IP, password, name, domain.
Requires MH_SNUSBASE_API_KEY environment variable.

API: https://api.snusbase.com/data/search
Auth: API key in 'Auth' header (NOT Authorization)
Rate limit: 2,048 requests per 12 hours
"""
from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Snusbase search types mapping
_SEARCH_TYPES = {
    "email": "email",
    "EMAIL": "email",
    "username": "username",
    "USERNAME": "username",
    "phone": "phone",
    "PHONE": "phone",
    "ip": "ip",
    "IP": "ip",
    "name": "name",
    "NAME": "name",
    "password": "password",
    "domain": "domain",
    "DOMAIN": "domain",
}


class SnusbasePlugin:
    """Search Snusbase breach database."""

    @property
    def name(self) -> str:
        return "Snusbase"

    @property
    def requires_api_key(self) -> bool:
        return True

    @property
    def stage(self) -> int:
        return 1

    @property
    def target_types(self) -> list[str]:
        return ["email", "username", "phone", "ip", "name", "password", "domain"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        search_type = _SEARCH_TYPES.get(target_type)
        if not search_type:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Snusbase supports email/username/phone/ip/name/password/domain, got {target_type}",
            )

        if not target or len(target) < 2:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Search target too short",
            )

        api_key = os.environ.get("MH_SNUSBASE_API_KEY", "")
        if not api_key:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="MH_SNUSBASE_API_KEY not configured",
            )

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("snusbase.com", self.name)

        url = "https://api.snusbase.com/data/search"
        headers = {
            "Auth": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        # Snusbase API: terms array + types array
        payload = {
            "terms": [target],
            "types": [search_type],
            "wildcard": False,
            "group_by": "db",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url, headers=headers, json=payload,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Parse Snusbase response: {"results": {db_name: [records]}, "size": N}
                        results = data.get("results", {})
                        if not results or data.get("size", 0) == 0:
                            return PluginResult(
                                plugin_name=self.name,
                                is_success=True,
                                data={
                                    "data_found": False,
                                    "target": target,
                                    "target_type": search_type,
                                    "source": "snusbase",
                                },
                            )

                        # Flatten results into breach list
                        breaches = []
                        for db_name, records in results.items():
                            if isinstance(records, list):
                                for record in records:
                                    breaches.append({
                                        "database": db_name,
                                        "fields": list(record.keys()) if isinstance(record, dict) else [],
                                        "data": record if isinstance(record, dict) else str(record),
                                    })
                            elif isinstance(records, dict):
                                breaches.append({
                                    "database": db_name,
                                    "fields": list(records.keys()),
                                    "data": records,
                                })

                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "data_found": True,
                                "target": target,
                                "target_type": search_type,
                                "source": "snusbase",
                                "breaches": breaches[:20],
                                "breach_count": len(breaches),
                                "databases": list(results.keys()),
                            },
                        )
                    elif resp.status == 401:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="Invalid API key (401 Unauthorized)",
                        )
                    elif resp.status == 429:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="Rate limit exceeded (429)",
                        )
                    else:
                        error_text = await resp.text()
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"HTTP {resp.status}: {error_text[:200]}",
                        )
        except aiohttp.ClientError as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Network error: {e}",
            )
        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=str(e),
            )
