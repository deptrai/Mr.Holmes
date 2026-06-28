"""Core/plugins/tiktok_vn.py — TikTok profile scraper.

Scrapes TikTok public profiles via tiktok.com using BrowserPool.
Extracts: nickname, bio, followers, following, likes, video count, profile pic.
Uses SIGI_STATE / __UNIVERSAL_DATA_FOR_REHYDRATION__ embedded JSON.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class TikTokVnPlugin:
    """Scrape TikTok public profile."""

    @property
    def name(self) -> str:
        return "TikTokVn"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["username", "USERNAME"]

    @property
    def tos_risk(self) -> str:
        return "tos_risk"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("username", "USERNAME", "url", "URL"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"TikTokVn supports username/url, got {target_type}",
            )

        # Determine username/URL
        if target_type in ("url", "URL") and "tiktok.com" in target:
            # Extract username from URL: https://www.tiktok.com/@username
            import re
            match = re.search(r'tiktok\.com/@([^/?]+)', target)
            username = match.group(1) if match else target.rstrip("/").split("@")[-1]
        else:
            username = target.strip().lstrip("@")

        if not username:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Invalid username",
            )

        url = f"https://www.tiktok.com/@{username}"

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
        await limiter.wait_if_needed("tiktok.com", self.name)

        try:
            async with PooledBrowserContext("tiktok") as ctx:
                page = await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Check for not found
                content = await page.content()
                if "couldn't find this account" in content.lower() or "page not available" in content.lower():
                    await page.close()
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": False,
                            "url": url,
                            "username": username,
                            "warning": "Profile not found",
                        },
                    )

                # Extract from SIGI_STATE or __UNIVERSAL_DATA_FOR_REHYDRATION__
                profile_data = await page.evaluate("""
                    () => {
                        const data = {};

                        // Method 1: SIGI_STATE
                        const sigiScript = document.getElementById('SIGI_STATE');
                        if (sigiScript) {
                            try {
                                const state = JSON.parse(sigiScript.textContent);
                                const users = state?.UserModule?.users || {};
                                const userKey = Object.keys(users)[0];
                                if (userKey && users[userKey]) {
                                    const u = users[userKey];
                                    data.unique_id = u.unique_id || '';
                                    data.nickname = u.nickname || '';
                                    data.signature = u.signature || '';
                                    data.bio = u.signature || '';
                                    data.profile_pic = u.avatar_larger || u.avatar_medium || u.avatar_thumb || '';
                                    data.is_verified = u.verified || false;
                                    data.sec_uid = u.sec_uid || '';
                                }
                                const stats = state?.UserModule?.stats || {};
                                const statsKey = Object.keys(stats)[0];
                                if (statsKey && stats[statsKey]) {
                                    const s = stats[statsKey];
                                    data.followers = s.followerCount || 0;
                                    data.following = s.followingCount || 0;
                                    data.likes = s.heart || s.heartCount || 0;
                                    data.video_count = s.videoCount || 0;
                                }
                            } catch(e) {
                                data._sigi_error = e.message;
                            }
                        }

                        // Method 2: __UNIVERSAL_DATA_FOR_REHYDRATION__
                        if (!data.nickname) {
                            const uniScript = document.getElementById('__UNIVERSAL_DATA_FOR_REHYDRATION__');
                            if (uniScript) {
                                try {
                                    const uni = JSON.parse(uniScript.textContent);
                                    const user = uni?.__defaultScope?.['webapp.user-detail']?.userInfo?.user;
                                    const stats = uni?.__defaultScope?.['webapp.user-detail']?.userInfo?.stats;
                                    if (user) {
                                        data.unique_id = user.uniqueId || '';
                                        data.nickname = user.nickname || '';
                                        data.signature = user.signature || '';
                                        data.bio = user.signature || '';
                                        data.profile_pic = user.avatarLarger || user.avatarMedium || '';
                                        data.is_verified = user.verified || false;
                                        data.sec_uid = user.secUid || '';
                                        data.tiktok_id = user.id || '';
                                    }
                                    if (stats) {
                                        data.followers = stats.followerCount || 0;
                                        data.following = stats.followingCount || 0;
                                        data.likes = stats.heartCount || 0;
                                        data.video_count = stats.videoCount || 0;
                                    }
                                } catch(e) {
                                    data._universal_error = e.message;
                                }
                            }
                        }

                        // Method 3: Meta tags fallback
                        if (!data.nickname) {
                            const metas = document.querySelectorAll('meta');
                            metas.forEach(m => {
                                const prop = m.getAttribute('property') || m.getAttribute('name');
                                const content = m.getAttribute('content');
                                if (prop && content) {
                                    if (prop === 'og:title') data.nickname = content.replace(' | TikTok', '').trim();
                                    if (prop === 'og:description') {
                                        data.description = content;
                                        const fMatch = content.match(/([\d.]+[KMkm]?)\s+Followers/);
                                        if (fMatch) data.followers = fMatch[1];
                                    }
                                    if (prop === 'og:image') data.profile_pic = content;
                                }
                            });
                        }

                        // Method 4: data-e2e attributes
                        if (!data.nickname) {
                            const nameEl = document.querySelector('[data-e2e="user-title"]');
                            if (nameEl) data.nickname = nameEl.innerText.trim();
                            const subEl = document.querySelector('[data-e2e="user-subtitle"]');
                            if (subEl) data.unique_id = subEl.innerText.trim().replace('@', '');
                            const bioEl = document.querySelector('[data-e2e="user-bio"]');
                            if (bioEl) data.bio = bioEl.innerText.trim();
                            const folEl = document.querySelector('[data-e2e="followers-count"]');
                            if (folEl) data.followers = folEl.innerText.trim();
                        }

                        data.title = document.title || '';
                        return data;
                    }
                """)

                await page.close()

                if profile_data and (profile_data.get("nickname") or profile_data.get("unique_id")):
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": True,
                            "url": url,
                            "username": username,
                            "platform": "tiktok",
                            **profile_data,
                        },
                    )

                return PluginResult(
                    plugin_name=self.name,
                    is_success=True,
                    data={
                        "data_found": False,
                        "url": url,
                        "username": username,
                        "warning": "Could not extract profile data (may require login)",
                    },
                )

        except Exception as e:
            logger.error("TikTokVn: scraping error: %s", e)
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Scraping error: {e}",
            )
