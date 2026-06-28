"""Core/plugins/facebook_vn.py — Facebook Vietnam scraper.

Scrapes Facebook profiles via mbasic.facebook.com (basic mobile version,
lighter JS, less anti-bot). Uses BrowserPool for shared browser contexts.

Extracts: name, bio, location, work, education, friends count, profile pic.
Handles login wall gracefully (returns partial + warning).
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class FacebookVnPlugin:
    """Scrape Facebook profile via mbasic.facebook.com."""

    @property
    def name(self) -> str:
        return "FacebookVn"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["username", "name", "phone"]

    @property
    def tos_risk(self) -> str:
        return "tos_risk"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("username", "USERNAME", "name", "NAME", "phone", "PHONE", "url", "URL"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"FacebookVn supports username/name/phone/url, got {target_type}",
            )

        # Determine profile URL
        if target_type in ("url", "URL") and "facebook.com" in target:
            url = target if target.startswith("http") else f"https://{target}"
            # Convert to mbasic
            url = url.replace("www.facebook.com", "mbasic.facebook.com")
            url = url.replace("https://facebook.com", "https://mbasic.facebook.com")
        else:
            url = f"https://mbasic.facebook.com/{target}"

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
        await limiter.wait_if_needed("mbasic.facebook.com", self.name)

        try:
            async with PooledBrowserContext("facebook") as ctx:
                page = await ctx.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)

                # Check for login wall
                content = await page.content()
                content_lower = content.lower()
                is_login_wall = (
                    ("login" in content_lower or "log in" in content_lower or "loginform" in content_lower)
                    and ("email" in content_lower or "password" in content_lower or "pass" in content_lower)
                )
                if is_login_wall:
                    await page.close()
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": False,
                            "url": url,
                            "warning": "Login wall — profile requires authentication",
                        },
                    )

                # Extract profile data from mbasic.facebook.com
                profile_data = await page.evaluate("""
                    () => {
                        const data = {};
                        // Profile name
                        const nameEl = document.querySelector('#m-timeline-cover-section h1, .bp9cbjyn.j83agx80, strong');
                        if (nameEl) data.name = nameEl.innerText.trim();

                        // Profile picture
                        const imgEl = document.querySelector('img[src*="fbcdn"], img.profpic');
                        if (imgEl) data.profile_pic = imgEl.src;

                        // Bio/About info
                        const aboutEl = document.querySelector('#bio, .biographical');
                        if (aboutEl) data.bio = aboutEl.innerText.trim();

                        // Friends count
                        const friendsEl = document.querySelector('a[href*="friends"]');
                        if (friendsEl) data.friends_link = friendsEl.href;

                        // Meta description
                        const metaDesc = document.querySelector('meta[name="description"]');
                        if (metaDesc) data.meta_description = metaDesc.content;

                        // Title
                        data.title = document.title || '';

                        // Extract all text from profile sections
                        const sections = document.querySelectorAll('#m_timeline_sections div, .timeline .timelineUnitContainer');
                        data.sections = [];
                        sections.forEach((s, i) => {
                            if (i < 10) {
                                const text = s.innerText.trim().substring(0, 500);
                                if (text) data.sections.push(text);
                            }
                        });

                        return data;
                    }
                """)

                await page.close()

                # Only report data_found when we have a real profile name or
                # meaningful sections — a generic title like "Facebook" alone
                # usually indicates a login wall / interstitial that slipped
                # past the earlier check.
                has_real_data = bool(
                    profile_data.get("name")
                    or (profile_data.get("sections") and len(profile_data["sections"]) > 0)
                    or (profile_data.get("meta_description"))
                )
                if profile_data and has_real_data:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": True,
                            "url": url,
                            "platform": "facebook",
                            **profile_data,
                        },
                    )

                return PluginResult(
                    plugin_name=self.name,
                    is_success=True,
                    data={
                        "data_found": False,
                        "url": url,
                        "warning": "Profile not found or private",
                    },
                )

        except Exception as e:
            logger.error("FacebookVn: scraping error: %s", e)
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Scraping error: {e}",
            )
