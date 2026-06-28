"""Core/plugins/vn_vehicle.py — Vietnam vehicle registration lookup.

Searches public vehicle information from Vietnam:
1. CSGT (Cảnh sát giao thông) — traffic violation lookup by license plate
   URL: https://www.csgt.vn/tra-cuu-phat-nguoi
2. VR (Cục Đăng kiểm Việt Nam) — inspection certificate lookup
   URL: https://gcndangkiem.vr.org.vn

Both require CAPTCHA — plugin handles gracefully.

License plate format: 29A-12345 (car) or 29-X1 234.56 (motorcycle)
"""
from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Vietnam license plate regex: 29A-12345, 29-X1 234.56, etc.
_PLATE_REGEX = re.compile(r'^\d{2}[A-Z]-?\d{3,5}$|^\d{2}-[A-Z]\d?\s?\d{3}\.?\d{2}$', re.IGNORECASE)


class VnVehiclePlugin:
    """Look up Vietnam vehicle registration and traffic violations."""

    @property
    def name(self) -> str:
        return "VnVehicle"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["license_plate", "LICENSE_PLATE", "plate", "PLATE", "name", "NAME"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("license_plate", "LICENSE_PLATE", "plate", "PLATE", "name", "NAME"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnVehicle supports license_plate/name, got {target_type}",
            )

        plate = target.strip().upper()
        if not plate or len(plate) < 4:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Invalid license plate: {target}",
            )

        # Method 1: CSGT traffic violation lookup
        csgt_result = await self._csgt_lookup(plate)

        # Method 2: VR inspection lookup
        vr_result = await self._vr_lookup(plate)

        # Combine results
        data_found = (csgt_result and csgt_result.get("data_found")) or \
                     (vr_result and vr_result.get("data_found"))

        result_data: dict[str, Any] = {
            "data_found": data_found,
            "license_plate": plate,
            "source": "csgt.vn + vr.org.vn",
        }

        if csgt_result:
            result_data["traffic_violations"] = csgt_result.get("violations", [])
            result_data["violation_count"] = csgt_result.get("count", 0)
            if csgt_result.get("error"):
                result_data["csgt_error"] = csgt_result["error"]

        if vr_result:
            result_data["inspection"] = vr_result.get("inspection", {})
            if vr_result.get("error"):
                result_data["vr_error"] = vr_result["error"]

        if not data_found:
            warnings = []
            if csgt_result and csgt_result.get("error"):
                warnings.append(f"CSGT: {csgt_result['error']}")
            if vr_result and vr_result.get("error"):
                warnings.append(f"VR: {vr_result['error']}")
            result_data["warning"] = " | ".join(warnings) if warnings else "No records found"

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data=result_data,
        )

    async def _csgt_lookup(self, plate: str) -> dict | None:
        """Search CSGT for traffic violations by license plate."""
        try:
            from Core.browser.browser_pool import PooledBrowserContext
        except ImportError:
            return {"data_found": False, "error": "BrowserPool not available"}

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("csgt.vn", self.name)

        try:
            async with PooledBrowserContext("vn_vehicle_csgt") as ctx:
                page = await ctx.new_page()
                url = "https://www.csgt.vn/tra-cuu-phat-nguoi"
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Check for CAPTCHA
                captcha = await page.query_selector(
                    "img[src*='captcha'], #captcha, .g-recaptcha, #imgCaptcha"
                )
                if captcha:
                    await page.close()
                    return {
                        "data_found": False,
                        "error": "CAPTCHA required on csgt.vn",
                    }

                # Try to fill license plate field
                plate_input = await page.query_selector(
                    "input[name*='plate'], input[name*='bienso'], #txtBienSo, input[placeholder*='biển']"
                )
                if plate_input:
                    await plate_input.fill(plate)
                    # Try to submit
                    submit = await page.query_selector(
                        "button[type='submit'], input[type='submit'], button:has-text('Tra cứu')"
                    )
                    if submit:
                        await submit.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)

                # Check for CAPTCHA after submit
                captcha = await page.query_selector("img[src*='captcha'], #captcha, .g-recaptcha")
                if captcha:
                    await page.close()
                    return {
                        "data_found": False,
                        "error": "CAPTCHA required after submit on csgt.vn",
                    }

                # Extract violation results
                results = await page.evaluate("""
                    () => {
                        const violations = [];
                        const rows = document.querySelectorAll('table tr, .result-item, .violation');
                        rows.forEach((row, i) => {
                            if (i >= 10 || i === 0) return;  // Skip header
                            const cells = row.querySelectorAll('td');
                            if (cells.length >= 3) {
                                violations.push({
                                    date: cells[0]?.innerText.trim() || '',
                                    location: cells[1]?.innerText.trim() || '',
                                    violation_type: cells[2]?.innerText.trim() || '',
                                    fine: cells[3]?.innerText.trim() || '',
                                    status: cells[4]?.innerText.trim() || '',
                                });
                            }
                        });
                        return {violations, title: document.title};
                    }
                """)

                await page.close()

                if results and results.get("violations"):
                    return {
                        "data_found": True,
                        "violations": results["violations"],
                        "count": len(results["violations"]),
                    }

                return {"data_found": False, "violations": [], "count": 0}

        except Exception as e:
            logger.error("VnVehicle CSGT error: %s", e)
            return {"data_found": False, "error": f"CSGT scrape error: {e}"}

    async def _vr_lookup(self, plate: str) -> dict | None:
        """Search Vietnam Register for inspection certificate."""
        try:
            from Core.browser.browser_pool import PooledBrowserContext
        except ImportError:
            return {"data_found": False, "error": "BrowserPool not available"}

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("vr.org.vn", self.name)

        try:
            async with PooledBrowserContext("vn_vehicle_vr") as ctx:
                page = await ctx.new_page()
                url = "https://gcndangkiem.vr.org.vn"
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Check for CAPTCHA
                captcha = await page.query_selector(
                    "img[src*='captcha'], #captcha, .g-recaptcha"
                )
                if captcha:
                    await page.close()
                    return {
                        "data_found": False,
                        "error": "CAPTCHA required on vr.org.vn",
                    }

                # Try to fill plate number
                plate_input = await page.query_selector(
                    "input[name*='plate'], input[name*='bienso'], #txtBienSo, input[placeholder*='biển']"
                )
                if plate_input:
                    await plate_input.fill(plate)
                    # Need chassis number (last 6 digits) — skip if not available
                    chassis_input = await page.query_selector(
                        "input[name*='chassis'], input[name*='sokhung'], #txtSoKhung"
                    )
                    # Submit if possible
                    submit = await page.query_selector(
                        "button[type='submit'], input[type='submit'], button:has-text('Tra cứu')"
                    )
                    if submit:
                        await submit.click()
                        await page.wait_for_load_state("networkidle", timeout=15000)

                # Extract inspection results
                results = await page.evaluate("""
                    () => {
                        const data = {};
                        const rows = document.querySelectorAll('table tr, .info-row, .result-item');
                        rows.forEach(row => {
                            const label = row.querySelector('.label, th, .field-name');
                            const value = row.querySelector('.value, td:last-child, .field-value');
                            if (label && value) {
                                const key = label.innerText.trim().toLowerCase().replace(/[^a-z0-9]/g, '_');
                                data[key] = value.innerText.trim();
                            }
                        });
                        return {inspection: data, title: document.title};
                    }
                """)

                await page.close()

                if results and results.get("inspection") and len(results["inspection"]) > 0:
                    return {
                        "data_found": True,
                        "inspection": results["inspection"],
                    }

                return {"data_found": False, "inspection": {}}

        except Exception as e:
            logger.error("VnVehicle VR error: %s", e)
            return {"data_found": False, "error": f"VR scrape error: {e}"}
