"""Core/plugins/instagram.py — Instagram profile scraper.

Scrapes Instagram public profiles via instagram.com using BrowserPool.
Extracts: bio, followers, following, posts count, external URL, profile pic.
Handles private accounts gracefully.
"""
from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


class InstagramPlugin:
    """Scrape Instagram public profile."""

    @property
    def name(self) -> str:
        return "Instagram"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 2

    @property
    def target_types(self) -> list[str]:
        return ["username", "USERNAME", "email", "EMAIL"]

    @property
    def tos_risk(self) -> str:
        return "tos_risk"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("username", "USERNAME", "email", "EMAIL", "url", "URL"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Instagram supports username/email/url, got {target_type}",
            )

        # Determine username/URL
        if target_type in ("url", "URL") and "instagram.com" in target:
            username = target.rstrip("/").split("/")[-1]
        else:
            username = target.strip()

        if not username or len(username) < 1:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Invalid username",
            )

        url = f"https://www.instagram.com/{username}/"

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
        await limiter.wait_if_needed("instagram.com", self.name)

        try:
            async with PooledBrowserContext("instagram") as ctx:
                page = await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Check for private/not found
                content = await page.content()
                if "This account is private" in content:
                    await page.close()
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": True,
                            "url": url,
                            "username": username,
                            "is_private": True,
                            "warning": "Account is private",
                        },
                    )

                if "Sorry, this page isn't available" in content or "Page Not Found" in content:
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

                # Try extracting from JSON-LD or shared data
                profile_data = await page.evaluate("""
                    () => {
                        const data = {};

                        // Method 1: Meta tags
                        const metas = document.querySelectorAll('meta');
                        metas.forEach(m => {
                            const prop = m.getAttribute('property') || m.getAttribute('name');
                            const content = m.getAttribute('content');
                            if (prop && content) {
                                if (prop === 'og:title') data.name = content.replace(' • Instagram photos and videos', '').replace(' (@', ' (').trim();
                                if (prop === 'og:description') {
                                    data.description = content;
                                    // Parse followers from description
                                    const match = content.match(/([\d.,kmK]+)\s+Followers/);
                                    if (match) data.followers = match[1];
                                    const followingMatch = content.match(/([\d.,kmK]+)\s+Following/);
                                    if (followingMatch) data.following = followingMatch[1];
                                    const postsMatch = content.match(/([\d.,kmK]+)\s+Posts/);
                                    if (postsMatch) data.posts = postsMatch[1];
                                }
                                if (prop === 'og:image') data.profile_pic = content;
                            }
                        });

                        // Method 2: JSON-LD
                        const scriptLd = document.querySelector('script[type="application/ld+json"]');
                        if (scriptLd) {
                            try {
                                const ld = JSON.parse(scriptLd.textContent);
                                if (ld.name) data.name = ld.name;
                                if (ld.description) data.bio = ld.description;
                                if (ld.image) data.profile_pic = typeof ld.image === 'string' ? ld.image : (ld.image.url || ld.image[0]);
                                if (ld.url) data.url = ld.url;
                            } catch(e) {}
                        }

                        // Method 3: shared data script
                        const scripts = document.querySelectorAll('script[type="text/javascript"]');
                        for (const s of scripts) {
                            if (s.textContent.includes('window._sharedData')) {
                                try {
                                    const match = s.textContent.match(/window\._sharedData\s*=\s*({.+?});/);
                                    if (match) {
                                        const shared = JSON.parse(match[1]);
                                        const user = shared?.entry_data?.ProfilePage?.[0]?.graphql?.user;
                                        if (user) {
                                            data.biography = user.biography || '';
                                            data.external_url = user.external_url || '';
                                            data.followers = user.edge_followed_by?.count?.toString() || data.followers;
                                            data.following = user.edge_follow?.count?.toString() || data.following;
                                            data.posts = user.edge_owner_to_timeline_media?.count?.toString() || data.posts;
                                            data.is_private = user.is_private || false;
                                            data.is_verified = user.is_verified || false;
                                            data.profile_pic = user.profile_pic_url_hd || user.profile_pic_url || data.profile_pic;
                                            data.full_name = user.full_name || data.name;
                                        }
                                    }
                                } catch(e) {}
                            }
                        }

                        data.title = document.title || '';
                        return data;
                    }
                """)

                await page.close()

                if profile_data and (profile_data.get("name") or profile_data.get("username") or profile_data.get("title")):
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": True,
                            "url": url,
                            "username": username,
                            "platform": "instagram",
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
                        "warning": "Could not extract profile data",
                    },
                )

        except Exception as e:
            logger.error("Instagram: scraping error: %s", e)
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Scraping error: {e}",
            )
