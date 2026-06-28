"""Core/plugins/truecaller.py — Truecaller phone reverse lookup.

NOTE: Truecaller does NOT offer an official public API for phone reverse lookup.
The unofficial search5.truecaller.com endpoint has been deprecated/blocked.

This plugin attempts the unofficial endpoint as a best-effort lookup.
For production use, consider:
1. Truecaller for Business API (enterprise, contact sales)
2. GetContact (free tier available)
3. Numverify (carrier only, already integrated as VnPhone)

Requires MH_TRUECALLER_API_KEY environment variable (unofficial installationId).
"""
from __future__ import annotations

import logging
import os
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class TruecallerPlugin:
    """Reverse lookup phone number via Truecaller API."""

    @property
    def name(self) -> str:
        return "Truecaller"

    @property
    def requires_api_key(self) -> bool:
        return True

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["phone", "PHONE"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("phone", "PHONE"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Truecaller supports phone, got {target_type}",
            )

        # Sanitize phone number
        phone = re.sub(r'[^\d+]', '', target)
        if not phone or len(phone) < 7:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Invalid phone number: {target}",
            )

        api_key = os.environ.get("MH_TRUECALLER_API_KEY", "")
        if not api_key:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="MH_TRUECALLER_API_KEY not configured",
            )

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("api.truecaller.com", self.name)

        url = "https://search5.truecaller.com/v2/search"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        }
        params = {
            "q": phone,
            "countryCode": "",
            "type": "4",
            "locAddr": "",
            "placement": "SEARCHRESULTS,HISTORY,DETAILS",
            "clientId": "1",
            "encoding": "json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # Parse Truecaller response
                        records = data.get("data", [])
                        if not records:
                            return PluginResult(
                                plugin_name=self.name,
                                is_success=True,
                                data={
                                    "data_found": False,
                                    "phone": phone,
                                    "source": "truecaller",
                                },
                            )

                        # Primary record
                        record = records[0]
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "data_found": True,
                                "phone": phone,
                                "source": "truecaller",
                                "name": record.get("name", ""),
                                "email": record.get("email", ""),
                                "address": record.get("address", ""),
                                "country": record.get("country", ""),
                                "carrier": record.get("carrier", ""),
                                "spam_score": record.get("score", 0),
                                "spam_type": record.get("spamType", ""),
                                "gender": record.get("gender", ""),
                                "image": record.get("image", ""),
                                "id": record.get("id", ""),
                                "records": records[:3],
                                "count": len(records),
                            },
                        )
                    elif resp.status == 401:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message="Invalid API key (401 Unauthorized)",
                        )
                    elif resp.status == 404:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={"data_found": False, "phone": phone, "source": "truecaller"},
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
