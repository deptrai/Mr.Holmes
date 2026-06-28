"""Core/plugins/vncourt.py — Vietnam Court Records scraper.

Searches public court records from thuvienphapluat.vn — Vietnam's
largest legal document library with public court case database.

Uses Playwright stealth browser to scrape search results.
Rate limited to 1 request per 5 seconds (stricter than tax portal).
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class VnCourtPlugin:
    """Search Vietnam court records from thuvienphapluat.vn."""

    @property
    def name(self) -> str:
        return "VnCourt"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["name", "case_id"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("name", "NAME", "case_id", "CASE_ID", "business_name"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnCourt supports name/case_id, got {target_type}",
            )

        # Sanitize search query
        query = target.strip()
        if len(query) < 2:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Search query too short (min 2 chars)",
            )

        try:
            from Core.browser.browser_pool import PooledBrowserContext
        except ImportError:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="BrowserPool not available (Playwright not installed)",
            )

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("thuvienphapluat.vn", self.name)

        try:
            async with PooledBrowserContext("vncourt") as ctx:
                page = await ctx.new_page()

                # Search thuvienphapluat.vn court cases
                # Use the public search URL
                search_url = (
                    f"https://thuvienphapluat.vn/vn/banan/"
                    f"?q={query}&type=bancanhan"
                )
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

                # Wait for search results to load
                try:
                    await page.wait_for_selector(".result-item, .search-result, .ban-an-item", timeout=10000)
                except Exception:
                    # Results may not have those selectors — try generic
                    pass

                # Check for CAPTCHA
                captcha = await page.query_selector("img[src*='captcha']") or \
                          await page.query_selector("#captcha")
                if captcha:
                    logger.warning("VnCourt: CAPTCHA detected")
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": False,
                            "query": query,
                            "source": "thuvienphapluat.vn",
                            "warning": "CAPTCHA required — manual intervention needed",
                        },
                        error_message="CAPTCHA detected",
                    )

                # Extract search results
                results = await page.evaluate("""
                    () => {
                        const items = document.querySelectorAll('.result-item, .search-result, .ban-an-item, .item');
                        const cases = [];
                        items.forEach((item, i) => {
                            if (i >= 10) return;
                            const titleEl = item.querySelector('h3, h4, .title, a.title');
                            const linkEl = item.querySelector('a[href]');
                            const descEl = item.querySelector('.description, .desc, .summary, p');
                            cases.push({
                                title: titleEl ? titleEl.innerText.trim() : '',
                                url: linkEl ? linkEl.href : '',
                                snippet: descEl ? descEl.innerText.trim().substring(0, 300) : '',
                            });
                        });
                        return cases;
                    }
                """)

                await page.close()

                if results:
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": True,
                            "query": query,
                            "source": "thuvienphapluat.vn",
                            "cases": results,
                            "count": len(results),
                        },
                    )

                return PluginResult(
                    plugin_name=self.name,
                    is_success=True,
                    data={
                        "data_found": False,
                        "query": query,
                        "source": "thuvienphapluat.vn",
                        "cases": [],
                        "count": 0,
                    },
                )

        except Exception as e:
            logger.error("VnCourt: scraping error: %s", e)
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Scraping error: {e}",
            )
