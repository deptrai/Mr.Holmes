"""Core/plugins/linkedin.py — LinkedIn profile scraper.

Scrapes LinkedIn public profiles using BrowserPool.
Uses social-preview UA trick (facebookexternalhit) for SSR HTML with JSON-LD.

Extracts: name, headline, company, education, location, connections.
Handles auth wall gracefully (returns partial + warning).
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)


class LinkedInPlugin:
    """Scrape LinkedIn public profile."""

    @property
    def name(self) -> str:
        return "LinkedIn"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 3

    @property
    def target_types(self) -> list[str]:
        return ["username", "USERNAME", "name", "NAME", "url", "URL"]

    @property
    def tos_risk(self) -> str:
        return "tos_risk"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("username", "USERNAME", "name", "NAME", "url", "URL"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"LinkedIn supports username/name/url, got {target_type}",
            )

        # Determine profile URL
        if target_type in ("url", "URL") and "linkedin.com" in target:
            url = target if target.startswith("http") else f"https://{target}"
        elif target_type in ("username", "USERNAME"):
            url = f"https://www.linkedin.com/in/{target}/"
        else:
            # For name search, use Google dork approach
            url = f"https://www.linkedin.com/in/{target.replace(' ', '-').lower()}/"

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
        await limiter.wait_if_needed("linkedin.com", self.name)

        async def _stable_content(pg) -> str:
            """Retrieve page.content() robustly, retrying while the page is
            still navigating (LinkedIn redirects to the auth wall which races
            with content retrieval and raises
            "Unable to retrieve content because the page is navigating")."""
            last_err: Exception | None = None
            for _ in range(4):
                try:
                    return await pg.content()
                except Exception as exc:  # noqa: BLE001
                    last_err = exc
                    try:
                        await pg.wait_for_timeout(1000)
                    except Exception:
                        pass
            # Final attempt — let the exception propagate to the outer handler
            if last_err is not None:
                raise last_err
            return await pg.content()

        try:
            async with PooledBrowserContext("linkedin") as ctx:
                page = await ctx.new_page()

                # Use social-preview UA to get SSR HTML with JSON-LD
                await page.set_extra_http_headers({
                    "User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
                })

                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # LinkedIn redirects to the auth wall; let navigation settle
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=10000)
                except Exception:
                    pass
                try:
                    await page.wait_for_timeout(1500)
                except Exception:
                    pass

                # Check for auth wall
                content = await _stable_content(page)
                if ("authwall" in content.lower()) or (
                    "sign in" in content.lower() and len(content) < 10000
                ):
                    # Try without social-preview UA as fallback
                    await page.close()
                    page = await ctx.new_page()
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    try:
                        await page.wait_for_load_state("domcontentloaded", timeout=10000)
                    except Exception:
                        pass
                    try:
                        await page.wait_for_timeout(1500)
                    except Exception:
                        pass
                    content = await _stable_content(page)
                    if "authwall" in content.lower():
                        await page.close()
                        return PluginResult(
                            plugin_name=self.name,
                            is_success=True,
                            data={
                                "data_found": False,
                                "url": url,
                                "warning": "LinkedIn auth wall — profile requires authentication",
                            },
                        )

                # Extract from JSON-LD (most stable method per research)
                profile_data = await page.evaluate("""
                    () => {
                        const data = {};

                        // Method 1: JSON-LD schema
                        const ldScripts = document.querySelectorAll('script[type="application/ld+json"]');
                        ldScripts.forEach(script => {
                            try {
                                const ld = JSON.parse(script.textContent);
                                if (ld["@type"] === "Person") {
                                    data.name = ld.name || data.name;
                                    data.headline = ld.jobTitle || data.headline;
                                    if (typeof ld.worksFor === 'object') {
                                        data.company = ld.worksFor.name || '';
                                    } else if (typeof ld.worksFor === 'string') {
                                        data.company = ld.worksFor;
                                    }
                                    if (ld.address) {
                                        if (typeof ld.address === 'object') {
                                            data.location = ld.address.addressLocality || ld.address.addressRegion || '';
                                        } else {
                                            data.location = ld.address;
                                        }
                                    }
                                    if (ld.alumniOf) {
                                        data.education = [];
                                        if (Array.isArray(ld.alumniOf)) {
                                            ld.alumniOf.forEach(a => {
                                                if (typeof a === 'object') data.education.push(a.name || '');
                                                else data.education.push(a);
                                            });
                                        } else if (typeof ld.alumniOf === 'object') {
                                            data.education.push(ld.alumniOf.name || '');
                                        } else {
                                            data.education.push(ld.alumniOf);
                                        }
                                    }
                                    data.url = ld.url || data.url;
                                } else if (ld["@type"] === "Organization") {
                                    data.is_company = true;
                                    data.name = ld.name || data.name;
                                    data.description = ld.description || '';
                                    data.company_url = ld.url || '';
                                }
                            } catch(e) {}
                        });

                        // Method 2: Meta tags
                        const metas = document.querySelectorAll('meta');
                        metas.forEach(m => {
                            const prop = m.getAttribute('property') || m.getAttribute('name');
                            const content = m.getAttribute('content');
                            if (prop && content) {
                                if (prop === 'og:title') data.name = data.name || content.replace(' | LinkedIn', '').trim();
                                if (prop === 'og:description') data.description = data.description || content;
                                if (prop === 'og:image') data.profile_pic = content;
                                if (prop === 'title') data.title_meta = content;
                            }
                        });

                        // Method 3: CSS selectors (fallback, use semantic attrs)
                        if (!data.name) {
                            const nameEl = document.querySelector('h1, [data-control-name="identity"] h1');
                            if (nameEl) data.name = nameEl.innerText.trim();
                        }
                        if (!data.headline) {
                            const headlineEl = document.querySelector('.text-body-medium, h2');
                            if (headlineEl) data.headline = headlineEl.innerText.trim();
                        }
                        if (!data.location) {
                            const locEl = document.querySelector('.text-body-small.inline.t-black--light.break-words');
                            if (locEl) data.location = locEl.innerText.trim();
                        }

                        data.title = document.title || '';
                        return data;
                    }
                """)

                await page.close()

                if profile_data and (profile_data.get("name") or profile_data.get("title")):
                    return PluginResult(
                        plugin_name=self.name,
                        is_success=True,
                        data={
                            "data_found": True,
                            "url": url,
                            "platform": "linkedin",
                            **profile_data,
                        },
                    )

                return PluginResult(
                    plugin_name=self.name,
                    is_success=True,
                    data={
                        "data_found": False,
                        "url": url,
                        "warning": "Could not extract profile data (auth wall or not found)",
                    },
                )

        except Exception as e:
            logger.error("LinkedIn: scraping error: %s", e)
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"Scraping error: {e}",
            )
