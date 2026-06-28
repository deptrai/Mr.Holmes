"""Core/plugins/vn_business.py — Vietnamese business registry lookup.

Searches public business registration data from Vietnam.
Source: dangkykinhdoanh.gov.vn (Cổng thông tin quốc gia về đăng ký doanh nghiệp)

Two methods:
1. Public API endpoint (if available): dangkykinhdoanh.gov.vn/api/search
2. Browser scrape fallback via BrowserPool (Playwright)

v2.1 enhancements:
- Rate limiter integration (AD-12)
- BrowserPool fallback (AD-11)
- Structured output with business details
- Graceful CAPTCHA handling
"""
from __future__ import annotations

import logging
import re
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


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
        return ["tax_id", "TAX_ID", "business_name", "BUSINESS_NAME", "name", "NAME", "domain", "DOMAIN"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("tax_id", "TAX_ID", "business_name", "BUSINESS_NAME", "name", "NAME", "domain", "DOMAIN"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnBusiness supports tax_id/business_name/name/domain, got {target_type}",
            )

        # Validate Vietnamese tax code (10 or 13 digits)
        if target_type in ("tax_id", "TAX_ID"):
            clean = re.sub(r'\D', '', target)
            if len(clean) not in (10, 13):
                return PluginResult(
                    plugin_name=self.name,
                    is_success=False,
                    data={},
                    error_message=f"Invalid tax code: {target} (expected 10 or 13 digits)",
                )
            target = clean

        # Method 1: Try public API first
        api_result = await self._api_search(target)
        if api_result and api_result.get("data_found"):
            return PluginResult(
                plugin_name=self.name,
                is_success=True,
                data={**api_result, "source": "dangkykinhdoanh.gov.vn/api"},
            )

        # Method 2: Browser scrape fallback
        scrape_result = await self._browser_scrape(target)
        if scrape_result and scrape_result.get("data_found"):
            return PluginResult(
                plugin_name=self.name,
                is_success=True,
                data={**scrape_result, "source": "dangkykinhdoanh.gov.vn (scrape)"},
            )

        # Both methods returned no data
        if api_result and api_result.get("error"):
            error_msg = api_result["error"]
        elif scrape_result and scrape_result.get("error"):
            error_msg = scrape_result["error"]
        else:
            error_msg = None

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={
                "data_found": False,
                "query": target,
                "source": "dangkykinhdoanh.gov.vn",
                "warning": error_msg or "No business records found",
            },
            error_message=error_msg,
        )

    async def _api_search(self, target: str) -> dict | None:
        """Search via public API endpoint."""
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("dangkykinhdoanh.gov.vn", self.name)

        try:
            async with aiohttp.ClientSession() as session:
                url = "https://dangkykinhdoanh.gov.vn/api/search"
                params = {"keyword": target, "page": 1, "limit": 10}
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
                        businesses = data.get("data", data.get("results", []))
                        if businesses:
                            return {
                                "data_found": True,
                                "query": target,
                                "businesses": businesses[:5],
                                "count": len(businesses),
                                "primary": businesses[0] if businesses else None,
                            }
                        return {"data_found": False, "query": target}
                    else:
                        return {"data_found": False, "error": f"API HTTP {resp.status}"}
        except Exception as e:
            logger.warning("VnBusiness API error: %s", e)
            return {"data_found": False, "error": f"API error: {e}"}

    async def _browser_scrape(self, target: str) -> dict | None:
        """Fallback: scrape search results via BrowserPool."""
        try:
            from Core.browser.browser_pool import PooledBrowserContext
        except ImportError:
            return {"data_found": False, "error": "BrowserPool not available"}

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("dangkykinhdoanh.gov.vn", self.name)

        try:
            async with PooledBrowserContext("vn_business") as ctx:
                page = await ctx.new_page()
                search_url = f"https://dangkykinhdoanh.gov.vn/?q={target}"
                await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Check for CAPTCHA
                captcha = await page.query_selector("img[src*='captcha'], #captcha, .g-recaptcha")
                if captcha:
                    await page.close()
                    return {
                        "data_found": False,
                        "query": target,
                        "error": "CAPTCHA required — manual intervention needed",
                    }

                # Extract search results
                results = await page.evaluate("""
                    () => {
                        const businesses = [];
                        const rows = document.querySelectorAll('table tr, .search-result, .result-item, .business-item');
                        rows.forEach((row, i) => {
                            if (i >= 10) return;
                            const cells = row.querySelectorAll('td, .field, .info');
                            if (cells.length >= 2) {
                                const biz = {};
                                const fields = ['tax_code', 'name', 'address', 'status', 'type', 'representative'];
                                cells.forEach((cell, j) => {
                                    if (j < fields.length) {
                                        biz[fields[j]] = cell.innerText.trim();
                                    }
                                });
                                if (biz.name || biz.tax_code) businesses.push(biz);
                            }
                        });

                        // Also try meta description
                        const metaDesc = document.querySelector('meta[name="description"]');
                        const metaContent = metaDesc ? metaDesc.content : '';

                        return {businesses, metaContent, title: document.title};
                    }
                """)

                await page.close()

                if results and results.get("businesses"):
                    return {
                        "data_found": True,
                        "query": target,
                        "businesses": results["businesses"][:5],
                        "count": len(results["businesses"]),
                        "primary": results["businesses"][0],
                    }

                return {"data_found": False, "query": target}

        except Exception as e:
            logger.error("VnBusiness scrape error: %s", e)
            return {"data_found": False, "error": f"Scrape error: {e}"}
