"""
tests/engine/test_silent_exception_removal.py

Integration tests cho Story 4.4 — Remove Silent except Exception: pass.

Verifies:
    - AC1: Searcher.Scraping() errors surface via logger (không bị nuốt im)
    - AC2: registry._call_with_fallback() logs warning khi retry fails
    - AC4: Behavior preservation — dispatch vẫn tiếp tục sau lỗi
"""
from __future__ import annotations

import logging
import pytest
from unittest.mock import MagicMock, patch, call

from Core.scrapers.registry import ScraperRegistry
from Core.config.logging_config import _ROOT_LOGGER_NAME


# ---------------------------------------------------------------------------
# AC2 + AC4: ScraperRegistry._call_with_fallback logging
# ---------------------------------------------------------------------------

class TestScraperRegistryErrorHandling:
    """Verify registry._call_with_fallback logs instead of silently swallowing."""

    def test_connection_error_retries_without_proxy(self) -> None:
        """AC4: ConnectionError triggers retry with proxy=None."""
        calls = []
        def scraper_fn(proxy):
            calls.append(proxy)
            if proxy is not None:
                raise ConnectionError("proxy fail")

        registry = ScraperRegistry()
        registry._call_with_fallback(scraper_fn, {"https": "proxy"}, "conn error")

        assert len(calls) == 2
        assert calls[0] == {"https": "proxy"}
        assert calls[1] is None

    def test_retry_failure_logs_warning(self, caplog) -> None:
        """AC2: When retry also fails, logs warning instead of silently passing."""
        def always_fails(proxy):
            raise ConnectionError("fail")

        registry = ScraperRegistry()
        with caplog.at_level(logging.WARNING, logger=_ROOT_LOGGER_NAME):
            registry._call_with_fallback(always_fails, None, "conn error")

        assert any("retry" in r.message.lower() or "fail" in r.message.lower()
                   for r in caplog.records), \
            "Expected a warning log on retry failure"

    def test_generic_exception_logs_debug(self, caplog) -> None:
        """AC2: Generic (non-connection) exception logs debug level."""
        def broken_scraper(proxy):
            raise ValueError("unexpected error")

        registry = ScraperRegistry()
        with caplog.at_level(logging.DEBUG, logger=_ROOT_LOGGER_NAME):
            registry._call_with_fallback(broken_scraper, None, "conn error")

        debug_msgs = [r for r in caplog.records if r.levelno == logging.DEBUG]
        assert len(debug_msgs) >= 1

    def test_dispatch_continues_after_error(self) -> None:
        """AC4: Dispatch loop continues to next scraper after one fails."""
        succeeded = []

        def fail_scraper(proxy):
            raise RuntimeError("fail")

        def ok_scraper(proxy):
            succeeded.append("ok")

        registry = ScraperRegistry()
        registry.register("Fail", fail_scraper)
        registry.register("Ok", ok_scraper)

        registry.dispatch(["Fail", "Ok"], None)

        assert "ok" in succeeded


# ---------------------------------------------------------------------------
# AC1: Searcher.Scraping surfaces errors via logger
# ---------------------------------------------------------------------------

class TestSearcherScrapingLogging:
    """Verify Searcher.Scraping() no longer silently swallows scraper errors."""

    def test_scraping_error_logged_not_swallowed(self, caplog) -> None:
        """AC1: Scraper exception from Instagram reaches logger.error."""
        from Core.Searcher import MrHolmes

        with patch("Core.Support.Username.Scraper.info.Instagram",
                   side_effect=RuntimeError("instagram down")), \
             patch("Core.Support.Username.Scraper.info.Twitter"), \
             patch("Core.Support.Username.Scraper.info.TikTok"), \
             patch("Core.Support.Username.Scraper.info.Github"), \
             patch("Core.Support.Username.Scraper.info.GitLab"), \
             patch("Core.Support.Username.Scraper.info.Ngl"), \
             patch("Core.Support.Username.Scraper.info.Tellonym"), \
             patch("Core.Support.Username.Scraper.info.Gravatar"), \
             patch("Core.Support.Username.Scraper.info.Joinroll"), \
             patch("Core.Support.Username.Scraper.info.Chess"), \
             patch("os.path.isdir", return_value=True), \
             patch("os.chdir"), \
             caplog.at_level(logging.ERROR, logger=_ROOT_LOGGER_NAME):
            MrHolmes.Scraping("report.txt", "testuser", None, [], [], [], [])

        error_records = [r for r in caplog.records if r.levelno == logging.ERROR]
        assert len(error_records) >= 1
        assert "instagram down" in error_records[0].message.lower() or \
               "scraper" in error_records[0].message.lower()
