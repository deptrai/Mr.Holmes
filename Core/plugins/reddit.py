"""Core/plugins/reddit.py — Reddit user profile lookup.

Fetches public Reddit user data via the Reddit JSON API (no auth required).
"""
from __future__ import annotations
import aiohttp
from typing import Any

class RedditPlugin:
    """Reddit user profile lookup via public JSON API."""
    
    @property
    def name(self) -> str:
        return "Reddit"
    
    @property
    def requires_api_key(self) -> bool:
        return False
    
    @property
    def stage(self) -> int:
        return 2
    
    @property
    def target_types(self) -> list[str]:
        return ["username"]
    
    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult
        
        if target_type != "username":
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Reddit only supports username targets, got {target_type}"
            )
        
        try:
            async with aiohttp.ClientSession() as session:
                url = f"https://www.reddit.com/user/{target}/about.json"
                headers = {"User-Agent": "Mr.Holmes/2.0 OSINT Tool"}
                
                async with session.get(url, headers=headers, 
                                       timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status == 404:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"404 User not found: {target}"
                        )
                    if resp.status != 200:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=False,
                            data={},
                            error_message=f"HTTP {resp.status}"
                        )
                    
                    data = await resp.json()
                    user_data = data.get("data", {})
                    
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "username": user_data.get("name"),
                            "id": user_data.get("id"),
                            "karma": user_data.get("total_karma", 0),
                            "comment_karma": user_data.get("comment_karma", 0),
                            "link_karma": user_data.get("link_karma", 0),
                            "created_utc": user_data.get("created_utc"),
                            "is_verified": user_data.get("verified", False),
                            "is_employee": user_data.get("is_employee", False),
                            "is_mod": user_data.get("is_mod", False),
                            "is_gold": user_data.get("is_gold", False),
                            "avatar": user_data.get("icon_img"),
                            "url": f"https://www.reddit.com/user/{target}",
                        }
                    )
        except Exception as e:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=str(e)
            )
