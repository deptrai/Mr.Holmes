"""Core/plugins/vn_business.py — Vietnamese business registry lookup.

Searches public business registration data from Vietnam.
Source: dangkykinhdoanh.gov.vn (public government portal)
"""
from __future__ import annotations
import re
import aiohttp
from typing import Any

class VnBusinessPlugin:
    """Look up Vietnamese business registration by tax code or company name."""
    
    @property
    def name(self) -> str:
        return "VnBusiness"
    
    @property
    def requires_api_key(self) -> bool:
        return False
    
    @property
    def stage(self) -> int:
        return 3
    
    @property
    def target_types(self) -> list[str]:
        return ["tax_id", "business_name"]
    
    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult
        
        if target_type not in ("tax_id", "business_name", "domain"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnBusiness only supports tax_id/business_name targets, got {target_type}"
            )
        
        # Validate Vietnamese tax code (10 or 13 digits)
        if target_type == "tax_id":
            clean = re.sub(r'\D', '', target)
            if len(clean) not in (10, 13):
                return PluginResult(
                    plugin_name=self.name,
                    is_success=False,
                    data={},
                    error_message=f"Invalid tax code format: {target} (expected 10 or 13 digits)"
                )
            target = clean
        
        try:
            async with aiohttp.ClientSession() as session:
                # Search via public API endpoint
                url = "https://dangkykinhdoanh.gov.vn/api/search"
                params = {"keyword": target, "page": 1, "limit": 10}
                
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        businesses = data.get("data", data.get("results", []))
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "businesses": businesses[:5],
                                "count": len(businesses),
                                "query": target,
                            }
                        )
                    else:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"HTTP {resp.status}"
                        )
        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=str(e)
            )
    
    def normalize_target(self, target: str) -> str:
        return re.sub(r'\D', '', target) if target.replace('-','').replace(' ','').isdigit() else target.lower()
