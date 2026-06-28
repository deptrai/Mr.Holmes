"""Core/plugins/xinvoice.py — XInvoice API integration for Vietnam tax lookup.

XInvoice provides a REST API to look up Vietnamese taxpayer information
from the General Department of Taxation (Tổng cục Thuế) database.

API docs: https://xinvoice.vn/apis/tra-cuu-ma-so-thue-2
Requires: MH_XINVOICE_API_KEY environment variable
"""
from __future__ import annotations

import os
import re
from typing import Any

import aiohttp


class XInvoicePlugin:
    """Look up Vietnamese taxpayer info via XInvoice API."""

    @property
    def name(self) -> str:
        return "XInvoice"

    @property
    def requires_api_key(self) -> bool:
        return True

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["tax_id"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("tax_id", "TAX_ID", "domain", "business_name"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"XInvoice only supports tax_id, got {target_type}",
            )

        # Validate tax code: 10 digits, or 10+3 digits (branch)
        clean = re.sub(r'\D', '', target)
        if len(clean) not in (10, 13):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Invalid tax code: {target} (expected 10 or 13 digits)",
            )

        api_key = os.environ.get("MH_XINVOICE_API_KEY", "")
        if not api_key:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="MH_XINVOICE_API_KEY not configured",
            )

        # Rate limit
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("api.xinvoice.vn", self.name)

        url = f"https://api.xinvoice.vn/gdt-api/tax-payer-records/{clean}"
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        records = data.get("data", [])
                        if not records:
                            return PluginResult(
                                plugin_name=self.name,
                                is_success=True,
                                data={"data_found": False, "tax_id": clean, "records": []},
                            )
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "data_found": True,
                                "tax_id": clean,
                                "records": records[:5],
                                "count": len(records),
                                "primary": records[0] if records else None,
                            },
                        )
                    elif resp.status == 404:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={"data_found": False, "tax_id": clean, "records": []},
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
