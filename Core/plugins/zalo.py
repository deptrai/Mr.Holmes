"""Core/plugins/zalo.py — Zalo profile lookup.

Zalo is Vietnam's largest social media platform. Public profile data is
limited — most data requires authentication via Zalo API or webpack modules.

This plugin:
1. Tries Zalo Open API (if MH_ZALO_ACCESS_TOKEN configured)
2. Falls back to scraping zalo.me public profile page via BrowserPool

Extracts: name, avatar, status, cover photo (if public).
"""
from __future__ import annotations

import logging
import os
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class ZaloPlugin:
    """Look up Zalo profile via API or web scrape."""

    @property
    def name(self) -> str:
        return "Zalo"

    @property
    def requires_api_key(self) -> bool:
        return False  # API token is optional, web scrape is fallback

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["username", "USERNAME", "phone", "PHONE"]

    @property
    def tos_risk(self) -> str:
        return "tos_risk"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("username", "USERNAME", "phone", "PHONE", "url", "URL"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Zalo supports username/phone/url, got {target_type}",
            )

        # Determine Zalo ID/URL
        if target_type in ("url", "URL") and "zalo.me" in target:
            zalo_id = target.rstrip("/").split("/")[-1]
        else:
            zalo_id = target.strip()

        if not zalo_id:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Invalid Zalo ID",
            )

        # Method 1: Try Zalo Open API if token configured
        access_token = os.environ.get("MH_ZALO_ACCESS_TOKEN", "")
        if access_token:
            api_result = await self._api_lookup(access_token, zalo_id)
            if api_result:
                return api_result

        # Method 2: Web scrape zalo.me
        url = f"https://zalo.me/{zalo_id}"

        try:
            from Core.browser.browser_pool import PooledBrowserContext
        except ImportError:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="BrowserPool not available",
            )

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("zalo.me", self.name)

        try:
            async with PooledBrowserContext("zalo") as ctx:
                page = await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Zalo.me is a SPA — wait for content
                try:
                    await page.wait_for_timeout(3000)  # Give SPA time to render
                except Exception:
                    pass

                profile_data = await page.evaluate("""
                    () => {
                        const data = {};

                        // Meta tags
                        const metas = document.querySelectorAll('meta');
                        metas.forEach(m => {
                            const prop = m.getAttribute('property') || m.getAttribute('name');
                            const content = m.getAttribute('content');
                            if (prop && content) {
                                if (prop === 'og:title') data.name = content.trim();
                                if (prop === 'og:description') data.description = content.trim();
                                if (prop === 'og:image') data.avatar = content;
                            }
                        });

                        // Try to find profile elements (Zalo SPA)
                        const nameEl = document.querySelector('.profile-name, .user-name, h1, h2');
                        if (nameEl && !data.name) data.name = nameEl.innerText.trim();

                        const avatarEl = document.querySelector('.profile-avatar img, .avatar img, img[src*="zalo"]');
                        if (avatarEl && !data.avatar) data.avatar = avatarEl.src;

                        const statusEl = document.querySelector('.profile-status, .user-status, .status');
                        if (statusEl) data.status = statusEl.innerText.trim();

                        data.title = document.title || '';
                        return data;
                    }
                """)

                await page.close()

                # Detect HTTP error pages (403/404/etc.) so we don't report
                # the error-page title (e.g. "403 Forbidden") as a profile.
                title_lower = (profile_data.get("title") or "").lower().strip()
                name_lower = (profile_data.get("name") or "").lower().strip()
                is_error_page = any(
                    marker in title_lower or marker in name_lower
                    for marker in ("forbidden", "not found", "error", "access denied")
                )
                if is_error_page:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": False,
                            "url": url,
                            "zalo_id": zalo_id,
                            "warning": "Zalo returned an error page (blocked/not found)",
                        },
                    )

                if profile_data and (profile_data.get("name") or profile_data.get("title")):
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": True,
                            "url": url,
                            "zalo_id": zalo_id,
                            "platform": "zalo",
                            **profile_data,
                        },
                    )

                return PluginResult(
                    plugin_name=self.name,
                    is_success=True,
                    data={
                        "data_found": False,
                        "url": url,
                        "zalo_id": zalo_id,
                        "warning": "Zalo profile not found or requires authentication",
                    },
                )

        except Exception as e:
            logger.error("Zalo: scraping error: %s", e)
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Scraping error: {e}",
            )

    async def _api_lookup(self, access_token: str, zalo_id: str) -> Any:
        """Look up Zalo profile via Open API."""
        from Core.plugins.base import PluginResult
        from Core.utils.rate_limiter import RateLimiter

        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("graph.zalo.me", self.name)

        url = "https://graph.zalo.me/v2.0/me"
        headers = {
            "access_token": access_token,
            "Accept": "application/json",
        }
        params = {"fields": "id,name,avatar,cover,status"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, headers=headers, params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "data_found": True,
                                "zalo_id": zalo_id,
                                "platform": "zalo",
                                "source": "api",
                                "name": data.get("name", ""),
                                "avatar": data.get("avatar", ""),
                                "cover": data.get("cover", ""),
                                "status": data.get("status", ""),
                                "zalo_user_id": data.get("id", ""),
                            },
                        )
        except Exception as e:
            logger.warning("Zalo API lookup error: %s", e)

        return None
