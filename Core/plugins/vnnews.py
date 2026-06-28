"""Core/plugins/vnnews.py — Vietnam News Archive search.

Searches Vietnam news archives for articles mentioning a person or company.
Uses Google News search + site-specific dorks for major Vietnam newspapers:

- tuoitre.vn
- vnexpress.net
- thanhnien.vn
- dantri.com.vn
- nld.com.vn (Người Lao Động)

Does NOT scrape newspaper sites directly (anti-bot protection).
Instead uses Google search with site: operators.
"""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)

# Major Vietnam news sites to search
_VN_NEWS_SITES = [
    "tuoitre.vn",
    "vnexpress.net",
    "thanhnien.vn",
    "dantri.com.vn",
    "nld.com.vn",
    "vietnamnet.vn",
    "baomoi.com",
]


class VnNewsPlugin:
    """Search Vietnam news archives via Google + site dorks."""

    @property
    def name(self) -> str:
        return "VnNews"

    @property
    def requires_api_key(self) -> bool:
        return False

    @property
    def stage(self) -> int:
        return 2  # News search is stage 2 (identity expansion)

    @property
    def target_types(self) -> list[str]:
        return ["name", "business_name", "company"]

    @property
    def tos_risk(self) -> str:
        return "safe"

    async def check(self, target: str, target_type: str) -> Any:
        from Core.plugins.base import PluginResult

        if target_type not in ("name", "NAME", "business_name", "company", "username"):
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message=f"VnNews supports name/business_name, got {target_type}",
            )

        query = target.strip()
        if len(query) < 2:
            return PluginResult(
                plugin_name=self.name,
                is_success=False,
                data={},
                error_message="Search query too short (min 2 chars)",
            )

        # Build Google search query with site: operators
        site_query = " OR ".join(f"site:{site}" for site in _VN_NEWS_SITES)
        full_query = f'"{query}" ({site_query})'

        # Use SearxNG if available, else fall back to direct Google News search
        articles = await self._search_via_google_news(query)
        if not articles:
            # Fallback: try SearxNG
            articles = await self._search_via_searxng(full_query)

        if articles:
            return PluginResult(
                plugin_name=self.name,
                is_success=True,
                data={
                    "data_found": True,
                    "query": query,
                    "source": "google_news + vn_newspapers",
                    "articles": articles[:15],
                    "count": len(articles),
                },
            )

        return PluginResult(
            plugin_name=self.name,
            is_success=True,
            data={
                "data_found": False,
                "query": query,
                "source": "google_news + vn_newspapers",
                "articles": [],
                "count": 0,
            },
        )

    async def _search_via_google_news(self, query: str) -> list[dict]:
        """Search Google News RSS feed for Vietnam articles."""
        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed("news.google.com", self.name)

        # Google News RSS feed (Vietnam edition)
        import urllib.parse
        encoded = urllib.parse.quote(query)
        rss_url = f"https://news.google.com/rss/search?q={encoded}+when:5y&hl=vi&gl=VN&ceid=VN:vi"

        articles = []
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    rss_url,
                    timeout=aiohttp.ClientTimeout(total=15),
                    headers={"User-Agent": "Mozilla/5.0 (compatible; MrHolmes/2.1)"},
                ) as resp:
                    if resp.status != 200:
                        logger.warning("VnNews: Google News HTTP %d", resp.status)
                        return []

                    text = await resp.text()
                    # Parse RSS XML (simple regex parse to avoid xml dependency)
                    import re
                    items = re.findall(
                        r'<item>(.*?)</item>', text, re.DOTALL
                    )
                    for item in items[:15]:
                        title_match = re.search(r'<title>(.*?)</title>', item, re.DOTALL)
                        link_match = re.search(r'<link>(.*?)</link>', item, re.DOTALL)
                        date_match = re.search(r'<pubDate>(.*?)</pubDate>', item, re.DOTALL)
                        source_match = re.search(r'<source[^>]*>(.*?)</source>', item, re.DOTALL)

                        title = title_match.group(1).strip() if title_match else ""
                        # Unescape CDATA
                        title = title.replace("<![CDATA[", "").replace("]]>", "")
                        link = link_match.group(1).strip() if link_match else ""
                        date = date_match.group(1).strip() if date_match else ""
                        source = source_match.group(1).strip() if source_match else ""

                        if title:
                            articles.append({
                                "title": title,
                                "url": link,
                                "date": date,
                                "source": source,
                            })
        except Exception as e:
            logger.warning("VnNews: Google News search error: %s", e)

        return articles

    async def _search_via_searxng(self, query: str) -> list[dict]:
        """Fallback: search via SearxNG instance if configured."""
        import os
        searxng_url = os.environ.get("MH_SEARXNG_URL", "")
        if not searxng_url:
            return []

        from Core.utils.rate_limiter import RateLimiter
        limiter = RateLimiter.get_instance()
        await limiter.wait_if_needed(searxng_url, self.name)

        articles = []
        try:
            async with aiohttp.ClientSession() as session:
                params = {"q": query, "format": "json", "categories": "news"}
                async with session.get(
                    f"{searxng_url}/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=15),
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for result in data.get("results", [])[:15]:
                            articles.append({
                                "title": result.get("title", ""),
                                "url": result.get("url", ""),
                                "date": result.get("publishedDate", ""),
                                "source": result.get("publishedDomain", ""),
                                "snippet": result.get("content", "")[:300],
                            })
        except Exception as e:
            logger.warning("VnNews: SearxNG fallback error: %s", e)

        return articles
