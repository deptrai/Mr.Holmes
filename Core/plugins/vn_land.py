"""Core/plugins/vn_land.py — Vietnam land registry lookup.

Searches public land use rights information from Vietnam.
Sources:
- dichvucong.dkt.gov.vn (Bộ Tài nguyên Môi trường)
- maps.dkt.gov.vn (land map portal)

Note: Vietnam land registry is largely offline/paper-based. Public online
access is limited to:
1. Land use planning (quy hoạch sử dụng đất)
2. Land price framework (khung giá đất)
3. Land auction announcements

Full sổ đỏ (land certificate) lookup requires in-person visit to district
land office (Văn phòng đăng ký đất đai).

This plugin searches publicly available land planning + price data.
"""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class VnLandPlugin:
    """Search Vietnam land registry public data."""

    @property
    def name(self) -> str:
        return "VnLand"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["address", "ADDRESS", "location", "LOCATION", "name", "NAME"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("address", "ADDRESS", "location", "LOCATION", "name", "NAME", "domain", "DOMAIN"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnLand supports address/location/name, got {target_type}",
            )

        query = target.strip()
        if len(query) < 3:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Search query too short (min 3 chars)",
            )

        # Try API first (land price framework)
        api_result = await self._api_land_price(query)
        if api_result and api_result.get("data_found"):
            return PluginResult(
                plugin_name=self.name,
                is_success=True,
                data={**api_result, "source": "dkt.gov.vn/api"},
            )

        # Browser scrape fallback
        scrape_result = await self._browser_scrape(query)
        if scrape_result and scrape_result.get("data_found"):
            return PluginResult(
                plugin_name=self.name,
                is_success=True,
                data={**scrape_result, "source": "dkt.gov.vn (scrape)"},
            )

        # No data found
        error_msg = None
        if api_result and api_result.get("error"):
            error_msg = api_result["error"]
        elif scrape_result and scrape_result.get("error"):
            error_msg = scrape_result["error"]

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={
                "data_found": False,
                "query": query,
                "source": "dkt.gov.vn",
                "warning": error_msg or "No land records found (full lookup requires in-person visit)",
            },
            error_message=error_msg,
        )

    async def _api_land_price(self, query: str) -> dict | None:
        """Search land price framework via public API."""
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("dkt.gov.vn", self.name)

        try:
            async with aiohttp.ClientSession() as session:
                # Try land price framework API
                url = "https://dkt.gov.vn/api/gia-dat/search"
                params = {"keyword": query, "page": 1, "limit": 10}
                headers = {
                    "User-Agent": "Mozilla/5.0 (compatible; MrHolmes/2.1)",
                    "Accept": "application/json",
                }

                async with session.get(
                    url, params=params, headers=headers,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        records = data.get("data", data.get("results", []))
                        if records:
                            return {
                                "data_found": True,
                                "query": query,
                                "land_records": records[:5],
                                "count": len(records),
                                "primary": records[0],
                            }
                        return {"data_found": False, "query": query}
                    return {"data_found": False, "error": f"API HTTP {resp.status}"}
        except Exception as e:
            logger.warning("VnLand API error: %s", e)
            return {"data_found": False, "error": f"API error: {e}"}

    async def _browser_scrape(self, query: str) -> dict | None:
        """Fallback: scrape land planning search via BrowserPool."""
        try:
            from Core.browser.browser_pool import PooledBrowserContext
        except ImportError:
            return {"data_found": False, "error": "BrowserPool not available"}

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("dkt.gov.vn", self.name)

        try:
            async with PooledBrowserContext("vn_land") as ctx:
                page = await ctx.new_page()
                # Search land planning portal
                search_url = f"https://dkt.gov.vn/?s={query}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Check for CAPTCHA
                captcha = await page.query_selector("img[src*='captcha'], #captcha, .g-recaptcha")
                if captcha:
                    await page.close()
                    return {
                        "data_found": False,
                        "query": query,
                        "error": "CAPTCHA required",
                    }

                # Extract results
                results = await page.evaluate("""
                    () => {
                        const records = [];
                        const items = document.querySelectorAll('.search-result, .result-item, .post, article, table tr');
                        items.forEach((item, i) => {
                            if (i >= 10) return;
                            const titleEl = item.querySelector('h2, h3, .title, a');
                            const linkEl = item.querySelector('a[href]');
                            const descEl = item.querySelector('.description, .excerpt, p, .summary');
                            if (titleEl || descEl) {
                                records.push({
                                    title: titleEl ? titleEl.innerText.trim() : '',
                                    url: linkEl ? linkEl.href : '',
                                    snippet: descEl ? descEl.innerText.trim().substring(0, 300) : '',
                                });
                            }
                        });
                        return {records, title: document.title};
                    }
                """)

                await page.close()

                if results and results.get("records"):
                    return {
                        "data_found": True,
                        "query": query,
                        "land_records": results["records"][:5],
                        "count": len(results["records"]),
                    }

                return {"data_found": False, "query": query}

        except Exception as e:
            logger.error("VnLand scrape error: %s", e)
            return {"data_found": False, "error": f"Scrape error: {e}"}
