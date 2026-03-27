"""
Core/scrapers/registry.py

ScraperRegistry — replaces 250 LOC copy-paste dispatch (48 Scraper.info.* calls).
Adding/removing scrapers now requires only 1 registry entry.

Story 1.4 — Scraper Registry Pattern, Epic 1.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Optional

from Core.Support import Font
from Core.Support import Language
from Core.config.logging_config import get_logger

filename = Language.Translation.Get_Language()

_logger = get_logger(__name__)


class ScraperRegistry:
    """
    Maps scraper names → callables and provides a generic dispatch loop.

    Usage:
        registry = ScraperRegistry.build_username_registry(
            report_path, username, ig_params, post_locs, post_gps, tw_params)
        registry.dispatch(scraper_sites, http_proxy)

    Adding a new scraper:
        registry.register("MySite", lambda p: Scraper.info.MySite(report, username, p, ...))
    """

    def __init__(self) -> None:
        self._registry: Dict[str, Callable] = {}

    # ------------------------------------------------------------------
    # Registration API
    # ------------------------------------------------------------------
    def register(self, name: str, fn: Callable) -> "ScraperRegistry":
        """
        Register a scraper callable under the given name.

        The callable must accept a single argument: http_proxy (dict or None).

        Returns self to support fluent chaining:
            registry.register("A", fn_a).register("B", fn_b)
        """
        if not callable(fn):
            raise TypeError("ScraperRegistry.register: fn must be callable, got {!r}".format(type(fn)))
        self._registry[name] = fn
        return self

    def registered_names(self) -> List[str]:
        """Return list of registered scraper names."""
        return list(self._registry.keys())

    # ------------------------------------------------------------------
    # Dispatch API
    # ------------------------------------------------------------------
    def dispatch(self, scraper_sites: List[str], http_proxy: Optional[dict]) -> None:
        """
        For each name in scraper_sites that is registered, call its scraper.

        Proxy fallback behaviour (matches original):
          1. Try with http_proxy
          2. On ConnectionError → print warning and retry with proxy=None
          3. On any other Exception → silently continue
        """
        connection_error_msg = Language.Translation.Translate_Language(
            filename, "Default", "Connection_Error1", "None")

        for site_name in scraper_sites:
            scraper_fn = self._registry.get(site_name)
            if scraper_fn is None:
                continue
            self._call_with_fallback(scraper_fn, http_proxy, connection_error_msg)

    def _call_with_fallback(
        self,
        scraper_fn: Callable,
        http_proxy: Optional[dict],
        connection_error_msg: str,
    ) -> None:
        """
        Invoke scraper_fn(http_proxy). On ConnectionError, retry with proxy=None.
        Swallows all remaining exceptions to keep the dispatch loop alive.
        """
        try:
            scraper_fn(http_proxy)
        except ConnectionError:
            _logger.warning("Connection error, retrying without proxy: %s", connection_error_msg)
            try:
                scraper_fn(None)
            except Exception as e:
                _logger.warning("Scraper retry without proxy also failed: %s", e)
        except Exception as e:
            _logger.debug("Scraper dispatch error (non-critical): %s", e)

    # ------------------------------------------------------------------
    # Factory: Username scan registry
    # ------------------------------------------------------------------
    @classmethod
    def build_username_registry(
        cls,
        report_path: str,
        username: str,
        instagram_params: list,
        post_locations: list,
        post_gps: list,
        twitter_params: list,
    ) -> "ScraperRegistry":
        """
        Build and return a ScraperRegistry pre-populated with all 19 username scrapers.

        This replaces the _build_scraper_map() module-level helper in scan_pipeline.py.
        Each scraper is registered with its canonical name (matching site_list.json keys).
        """
        from Core.Support.Username import Scraper

        registry = cls()

        # fmt: off
        registry.register("Instagram",   lambda p: Scraper.info.Instagram(
            report_path, username, p, instagram_params, post_locations,
            post_gps, "Usernames", username))
        registry.register("Twitter",     lambda p: Scraper.info.Twitter(
            report_path, username, p, twitter_params, "Usernames", username))
        registry.register("TikTok",      lambda p: Scraper.info.TikTok(
            report_path, username, p, "Usernames", username))
        registry.register("GitHub",      lambda p: Scraper.info.Github(
            report_path, username, p, "Usernames", username))
        registry.register("GitLab",      lambda p: Scraper.info.GitLab(
            report_path, username, p, "Usernames", username))
        registry.register("Ngl.link",    lambda p: Scraper.info.Ngl(
            report_path, username, p, "Usernames", username))
        registry.register("Tellonym",    lambda p: Scraper.info.Tellonym(
            report_path, username, p, "Usernames", username))
        registry.register("Gravatar",    lambda p: Scraper.info.Gravatar(
            report_path, username, p, "Usernames", username))
        registry.register("JoinRoll",    lambda p: Scraper.info.Joinroll(
            report_path, username, p, "Usernames", username))
        registry.register("Chess.com",   lambda p: Scraper.info.Chess(
            report_path, username, p, "Usernames", username))
        registry.register("Minecraft",   lambda p: Scraper.info.Minecraft(
            report_path, username, p, "Usernames", username))
        registry.register("Disqus",      lambda p: Scraper.info.Disqus(
            report_path, username, p, "Usernames", username))
        registry.register("Imgur",       lambda p: Scraper.info.Imgur(
            report_path, username, p, "Usernames", username))
        registry.register("Pr0gramm",    lambda p: Scraper.info.Pr0gramm(
            report_path, username, p, "Usernames", username))
        registry.register("BinarySearch",lambda p: Scraper.info.Binarysearch(
            report_path, username, p, "Usernames", username))
        registry.register("MixCloud",    lambda p: Scraper.info.MixCloud(
            report_path, username, p, "Usernames", username))
        registry.register("DockerHub",   lambda p: Scraper.info.Dockerhub(
            report_path, username, p, "Usernames", username))
        registry.register("Kik",         lambda p: Scraper.info.Kik(
            report_path, username, p, "Usernames", username))
        registry.register("Wattpad",     lambda p: Scraper.info.Wattpad(
            report_path, username, p, "Usernames", username))
        # fmt: on

        return registry
