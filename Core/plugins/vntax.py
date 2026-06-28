"""Core/plugins/vntax.py — Vietnam Tax Portal scraper.

Scrapes taxpayer information from the General Department of Taxation
portal: https://tracuunnt.gdt.gov.vn/

No official API — uses Playwright stealth browser to scrape the public
search form. Rate limited to 1 request per 3 seconds to avoid IP ban.
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class VnTaxPlugin:
    """Scrape Vietnam tax code lookup from tracuunnt.gdt.gov.vn."""

    @property
    def name(self) -> str:
        return "VnTax"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["tax_id", "business_name"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("tax_id", "TAX_ID", "business_name", "name"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnTax supports tax_id/business_name, got {target_type}",
            )

        # Validate tax code if tax_id type
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

        # Try XInvoice API first if key is configured (faster, structured)
        import os
        if os.environ.get("MH_XINVOICE_API_KEY"):
            try:
                from Core.plugins.xinvoice import XInvoicePlugin
                xinvoice = XInvoicePlugin()
                if target_type in ("tax_id", "TAX_ID"):
                    result = await xinvoice.check(target, "tax_id")
                    if result.is_success and result.data.get("data_found"):
                        result.plugin_name = self.name  # relabel
                        result.data["source"] = "xinvoice"
                        return result
            except Exception as exc:
                logger.warning("VnTax: XInvoice fallback failed: %s", exc)

        # Fall back to browser scraping
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
        await limiter.wait_if_needed("tracuunnt.gdt.gov.vn", self.name)

        try:
            async with PooledBrowserContext("vntax") as ctx:
                page = await ctx.new_page()
                search_url = "https://tracuunnt.gdt.gov.vn/tcnnt/mstcn.jsp"
                await page.goto(search_url, wait_until="networkidle", timeout=30000)

                # Fill the search form
                # The portal has a tax code input field
                tax_input = await page.query_selector("input[name='mst']") or \
                            await page.query_selector("#mst") or \
                            await page.query_selector("input[type='text']")
                if tax_input:
                    await tax_input.fill(target)
                    # Try to find and click submit button
                    submit = await page.query_selector("input[type='submit']") or \
                             await page.query_selector("button[type='submit']") or \
                             await page.query_selector("button:has-text('Tra cứu')")
                    if submit:
                        await submit.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)

                # Check for CAPTCHA
                captcha = await page.query_selector("img[src*='captcha']") or \
                          await page.query_selector("#captcha")
                if captcha:
                    logger.warning("VnTax: CAPTCHA detected, returning partial result")
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": False,
                            "tax_id": target,
                            "source": "tracuunnt.gdt.gov.vn",
                            "warning": "CAPTCHA required — manual intervention needed",
                        },
                        error_message="CAPTCHA detected",
                    )

                # Extract result table
                content = await page.content()
                result_table = await page.query_selector("table.result") or \
                               await page.query_selector("table table")

                if result_table:
                    rows_data = await result_table.evaluate("""
                        (table) => {
                            const rows = Array.from(table.querySelectorAll('tr'));
                            return rows.map(row => {
                                const cells = Array.from(row.querySelectorAll('td'));
                                return cells.map(c => c.innerText.trim());
                            });
                        }
                    """)
                    # Parse rows into structured data
                    records = []
                    headers = []
                    for i, row in enumerate(rows_data):
                        if i == 0:
                            headers = [h.lower().replace(' ', '_') for h in row]
                            continue
                        if len(row) >= 3:
                            record = {}
                            for j, val in enumerate(row):
                                key = headers[j] if j < len(headers) else f"col_{j}"
                                record[key] = val
                            records.append(record)

                    await page.close()
                    if records:
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "data_found": True,
                                "tax_id": target,
                                "source": "tracuunnt.gdt.gov.vn",
                                "records": records[:5],
                                "count": len(records),
                                "primary": records[0],
                            },
                        )

                await page.close()
                return PluginResult(
                    plugin_name=self.name,
                    is_success=True,
                    data={
                        "data_found": False,
                        "tax_id": target,
                        "source": "tracuunnt.gdt.gov.vn",
                    },
                )

        except Exception as e:
            logger.error("VnTax: scraping error: %s", e)
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Scraping error: {e}",
            )
