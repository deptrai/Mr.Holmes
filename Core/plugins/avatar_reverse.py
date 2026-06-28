"""Core/plugins/avatar_reverse.py — Avatar reverse image search.

Performs reverse image search on an avatar URL to find other profiles
using the same image. Uses three sources:

1. Google Images (free, no API key — via Playwright)
2. Yandex Images (free, no API key — via Playwright)
3. FaceCheck.id API (requires MH_FACECHECK_API_KEY — facial recognition)

Input: image URL (e.g., from social media profile pic)
Output: list of URLs where same/similar image appears
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class AvatarReversePlugin:
    """Reverse search avatar image across Google, Yandex, FaceCheck.id."""

    @property
    def name(self) -> str:
        return "AvatarReverse"

    @property
    def requires_api_key(self) -> bool:
        return False  # FaceCheck key is optional

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["image_url", "IMAGE_URL", "url", "URL"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("image_url", "IMAGE_URL", "url", "URL", "username", "USERNAME"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"AvatarReverse supports image_url/url, got {target_type}",
            )

        image_url = target.strip()
        if not image_url or not (image_url.startswith("http") or image_url.startswith("data:")):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Invalid image URL: {target}",
            )

        results: dict[str, Any] = {
            "data_found": False,
            "image_url": image_url,
            "source": "avatar_reverse",
            "matches": [],
        }

        # Method 1: FaceCheck.id API (if key configured)
        facecheck_key = os.environ.get("MH_FACECHECK_API_KEY", "")
        if facecheck_key:
            facecheck_results = await self._facecheck_search(image_url, facecheck_key)
            if facecheck_results:
                results["matches"].extend(facecheck_results)
                results["data_found"] = True
                results["facecheck"] = True

        # Method 2: Google Images reverse search (via Playwright)
        google_results = await self._google_reverse_search(image_url)
        if google_results:
            results["matches"].extend(google_results)
            results["data_found"] = True
            results["google"] = True

        # Method 3: Yandex Images reverse search (via Playwright)
        yandex_results = await self._yandex_reverse_search(image_url)
        if yandex_results:
            results["matches"].extend(yandex_results)
            results["data_found"] = True
            results["yandex"] = True

        results["match_count"] = len(results["matches"])

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data=results,
        )

    async def _facecheck_search(self, image_url: str, api_key: str) -> list[dict]:
        """Search FaceCheck.id API for face matches.

        API workflow (per research):
        1. POST /api/upload_pic (multipart) → returns id_search
        2. POST /api/search with id_search → poll until progress=100
        3. Parse output.items[].url, score, domain, category

        Auth: Authorization: APITOKEN
        Cost: 3 credits ($0.30) per search
        """
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("facecheck.id", self.name)

        matches = []
        try:
            async with aiohttp.ClientSession() as session:
                # Step 1: Download image, then upload as multipart
                # FaceCheck requires multipart/form-data upload, not URL
                image_data = None
                async with session.get(
                    image_url, timeout=aiohttp.ClientTimeout(total=15)
                ) as img_resp:
                    if img_resp.status == 200:
                        image_data = await img_resp.read()

                if not image_data:
                    logger.warning("FaceCheck: could not download image from %s", image_url)
                    return []

                upload_url = "https://facecheck.id/api/upload_pic"
                headers = {"Authorization": api_key, "Accept": "application/json"}
                form = aiohttp.FormData()
                form.add_field("images", image_data, filename="avatar.jpg", content_type="image/jpeg")
                form.add_field("id_search", "")

                async with session.post(
                    upload_url, headers=headers, data=form,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("FaceCheck upload HTTP %d", resp.status)
                        return []
                    data = await resp.json()
                    if data.get("error"):
                        logger.warning("FaceCheck upload error: %s", data["error"])
                        return []
                    search_id = data.get("id_search", "")

                if not search_id:
                    return []

                # Step 2: Search (poll for results)
                search_url = "https://facecheck.id/api/search"
                search_payload = {
                    "id_search": search_id,
                    "with_progress": True,
                    "status_only": False,
                }

                for _ in range(15):  # Max 15 polls (45s total)
                    await limiter.wait_if_needed("facecheck.id", self.name)
                    async with session.post(
                        search_url, headers=headers, json=search_payload,
                        timeout=aiohttp.ClientTimeout(total=30),
                    ) as resp:
                        if resp.status != 200:
                            break
                        data = await resp.json()
                        progress = data.get("progress", 0)
                        if progress >= 100:
                            items = data.get("output", {}).get("items", [])
                            for item in items[:10]:
                                score = item.get("score", 0)
                                matches.append({
                                    "source": "facecheck",
                                    "url": item.get("url", ""),
                                    "domain": item.get("domain", ""),
                                    "category": item.get("category", ""),
                                    "score": score,
                                    "confidence": "high" if score > 0.85 else ("medium" if score > 0.7 else "low"),
                                    "image": item.get("image", ""),
                                })
                            break
                        # Still processing — wait and retry
                        import asyncio
                        await asyncio.sleep(3)

        except Exception as e:
            logger.warning("FaceCheck search error: %s", e)

        return matches

    async def _google_reverse_search(self, image_url: str) -> list[dict]:
        """Reverse search via Google Images using Playwright."""
        try:
            from Core.browser.browser_pool import PooledBrowserContext
        except ImportError:
            return []

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("images.google.com", self.name)

        matches = []
        try:
            async with PooledBrowserContext("google_images") as ctx:
                page = await ctx.new_page()
                # Go to Google Images
                await page.goto("https://images.google.com", wait_until="domcontentloaded", timeout=20000)

                # Click camera icon (search by image)
                camera_btn = await page.query_selector('div[aria-label="Search by image"], button[aria-label="Search by image"]')
                if camera_btn:
                    await camera_btn.click()
                    await page.wait_for_timeout(1000)

                # Paste URL
                url_input = await page.query_selector('input[type="url"], input[placeholder*="URL"]')
                if url_input:
                    await url_input.fill(image_url)
                    # Submit
                    search_btn = await page.query_selector('button[type="submit"], button:has-text("Search")')
                    if search_btn:
                        await search_btn.click()
                    await page.wait_for_load_state("networkidle", timeout=15000)

                    # Extract "Pages that include matching images"
                    results = await page.evaluate("""
                        () => {
                            const matches = [];
                            // Look for result links
                            const links = document.querySelectorAll('a[href]:not([href*="google.com"])');
                            links.forEach((link, i) => {
                                if (i >= 10) return;
                                const href = link.href;
                                const text = link.innerText.trim();
                                if (href && text && href.startsWith('http')) {
                                    matches.push({url: href, title: text.substring(0, 200)});
                                }
                            });
                            return matches;
                        }
                    """)
                    for r in results:
                        matches.append({
                            "source": "google_images",
                            "url": r.get("url", ""),
                            "title": r.get("title", ""),
                            "confidence": "exact_match",
                        })

                await page.close()
        except Exception as e:
            logger.warning("Google reverse search error: %s", e)

        return matches

    async def _yandex_reverse_search(self, image_url: str) -> list[dict]:
        """Reverse search via Yandex Images using Playwright."""
        try:
            from Core.browser.browser_pool import PooledBrowserContext
        except ImportError:
            return []

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("yandex.com", self.name)

        matches = []
        try:
            async with PooledBrowserContext("yandex_images") as ctx:
                page = await ctx.new_page()
                # Yandex Images search by URL
                yandex_url = f"https://yandex.com/images/search?rpt=imageview&url={image_url}"
                await page.goto(yandex_url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)

                # Extract "Sites containing image" results
                results = await page.evaluate("""
                    () => {
                        const matches = [];
                        const links = document.querySelectorAll('a[href]');
                        const excludeDomains = ['yandex.com', 'yandex.net', 'yandex.ru', 'mds.yandex'];
                        links.forEach((link, i) => {
                            if (i >= 20) return;
                            const href = link.href || '';
                            const text = link.innerText.trim();
                            // Exclude yandex domains and search-result-page URLs
                            const isExcluded = excludeDomains.some(d => href.includes(d)) ||
                                               href.includes('/images/search') ||
                                               href.includes('/images?') ||
                                               href.includes('rpt=imageview');
                            if (isExcluded) return;
                            if (href && text && href.startsWith('http') && text.length > 5) {
                                matches.push({url: href, title: text.substring(0, 200)});
                            }
                        });
                        return matches;
                    }
                """)
                for r in results:
                    matches.append({
                        "source": "yandex_images",
                        "url": r.get("url", ""),
                        "title": r.get("title", ""),
                        "confidence": "similar",
                    })

                await page.close()
        except Exception as e:
            logger.warning("Yandex reverse search error: %s", e)

        return matches
