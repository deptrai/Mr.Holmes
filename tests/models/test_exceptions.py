"""
tests/models/test_exceptions.py

Unit tests cho Story 2.4 — Custom Exception Classes.

Test coverage:
    - AC1: Exception hierarchy (all extend OSINTError)
    - AC2: All 5 exception classes exist
    - AC3: Structured context attributes per exception
    - AC4: Integration — async_search raises typed exceptions (through ScanResult)
    - AC5: Logging-friendly str() representation with context
"""
from __future__ import annotations

import asyncio
import pytest

from Core.models.exceptions import (
    OSINTError,
    TargetSiteTimeout,
    ProxyDeadError,
    RateLimitExceeded,
    ScraperError,
    ConfigurationError,
    SiteCheckError,
)
from Core.models import ScanStatus


# ---------------------------------------------------------------------------
# AC1 — Exception hierarchy
# ---------------------------------------------------------------------------

class TestExceptionHierarchy:
    def test_osint_error_is_base_exception(self):
        assert issubclass(OSINTError, Exception)

    def test_target_site_timeout_extends_osint_error(self):
        assert issubclass(TargetSiteTimeout, OSINTError)

    def test_proxy_dead_error_extends_osint_error(self):
        assert issubclass(ProxyDeadError, OSINTError)

    def test_rate_limit_exceeded_extends_osint_error(self):
        assert issubclass(RateLimitExceeded, OSINTError)

    def test_scraper_error_extends_osint_error(self):
        assert issubclass(ScraperError, OSINTError)

    def test_site_check_error_extends_osint_error(self):
        assert issubclass(SiteCheckError, OSINTError)

    def test_configuration_error_extends_osint_error(self):
        assert issubclass(ConfigurationError, OSINTError)


# ---------------------------------------------------------------------------
# AC2 + AC3 — TargetSiteTimeout
# ---------------------------------------------------------------------------

class TestTargetSiteTimeout:
    def test_creation_with_context(self):
        exc = TargetSiteTimeout(site_name="GitHub", url="https://github.com/u", timeout_seconds=15)
        assert exc.site_name == "GitHub"
        assert exc.url == "https://github.com/u"
        assert exc.timeout_seconds == 15

    def test_default_timeout(self):
        exc = TargetSiteTimeout(site_name="Site", url="https://s.com")
        assert exc.timeout_seconds == 10.0

    def test_str_contains_context(self):
        exc = TargetSiteTimeout(site_name="Twitter", url="https://t.com/u", timeout_seconds=5)
        s = str(exc)
        assert "Twitter" in s
        assert "5" in s

    def test_isinstance_osint_error(self):
        exc = TargetSiteTimeout("S", "https://s.com")
        assert isinstance(exc, OSINTError)


# ---------------------------------------------------------------------------
# AC2 + AC3 — ProxyDeadError
# ---------------------------------------------------------------------------

class TestProxyDeadError:
    def test_creation_with_context(self):
        exc = ProxyDeadError(proxy_url="http://p:8080", site_name="GitHub", url="https://github.com")
        assert exc.proxy_url == "http://p:8080"
        assert exc.site_name == "GitHub"
        assert exc.url == "https://github.com"

    def test_str_contains_proxy_and_site(self):
        exc = ProxyDeadError(proxy_url="http://p:8080", site_name="Reddit")
        s = str(exc)
        assert "http://p:8080" in s
        assert "Reddit" in s

    def test_url_optional(self):
        exc = ProxyDeadError(proxy_url="http://p:1", site_name="Site")
        assert exc.url == ""


# ---------------------------------------------------------------------------
# AC2 + AC3 — RateLimitExceeded
# ---------------------------------------------------------------------------

class TestRateLimitExceeded:
    def test_creation_http_429(self):
        exc = RateLimitExceeded(site_name="Reddit", url="https://r.com/u", status_code=429, retry_after=60)
        assert exc.status_code == 429
        assert exc.retry_after == 60

    def test_creation_http_403(self):
        exc = RateLimitExceeded(site_name="Instagram", url="https://ig.com/u", status_code=403)
        assert exc.status_code == 403
        assert exc.retry_after is None

    def test_str_includes_retry_after_when_present(self):
        exc = RateLimitExceeded("Site", "https://s.com", 429, retry_after=30)
        assert "30" in str(exc)

    def test_str_excludes_retry_after_when_absent(self):
        exc = RateLimitExceeded("Site", "https://s.com", 403)
        assert "retry_after" not in str(exc)


# ---------------------------------------------------------------------------
# AC2 + AC3 — ScraperError
# ---------------------------------------------------------------------------

class TestScraperError:
    def test_creation_with_original_error(self):
        cause = ValueError("parse failed")
        exc = ScraperError(scraper_name="Instagram", site_name="Instagram", original_error=cause)
        assert exc.scraper_name == "Instagram"
        assert exc.original_error is cause

    def test_str_includes_cause_type(self):
        cause = ConnectionError("refused")
        exc = ScraperError("TikTok", "TikTok", original_error=cause)
        assert "ConnectionError" in str(exc)

    def test_without_original_error(self):
        exc = ScraperError("GitHub", "GitHub")
        assert exc.original_error is None
        assert "GitHub" in str(exc)


# ---------------------------------------------------------------------------
# AC2 + AC3 — SiteCheckError (new in Story 2.4)
# ---------------------------------------------------------------------------

class TestSiteCheckError:
    def test_creation_with_all_attrs(self):
        cause = IOError("read failed")
        exc = SiteCheckError(
            site_name="Site", url="https://s.com",
            error_type="IOError", status_code=500, original_error=cause,
        )
        assert exc.site_name == "Site"
        assert exc.url == "https://s.com"
        assert exc.error_type == "IOError"
        assert exc.status_code == 500
        assert exc.original_error is cause

    def test_str_with_status_code(self):
        exc = SiteCheckError("Site", "https://s.com", error_type="ParseError", status_code=500)
        s = str(exc)
        assert "Site" in s
        assert "ParseError" in s
        assert "500" in s

    def test_str_with_original_error(self):
        cause = RuntimeError("unexpected")
        exc = SiteCheckError("Site", "https://s.com", error_type="RuntimeError", original_error=cause)
        assert "RuntimeError" in str(exc)

    def test_optional_status_code(self):
        exc = SiteCheckError("Site", "https://s.com", error_type="NetworkError")
        assert exc.status_code is None
        assert "http=" not in str(exc)

    def test_isinstance_hierarchy(self):
        exc = SiteCheckError("Site", "https://s.com", error_type="Err")
        assert isinstance(exc, OSINTError)
        assert isinstance(exc, Exception)


# ---------------------------------------------------------------------------
# AC4 — Integration: async_search raises typed exceptions via ScanResult
# ---------------------------------------------------------------------------

class TestAsyncSearchIntegration:
    """
    AC4 — Verify async_search.search_site() returns ScanResult with typed error messages.
    Tests use aioresponses to mock HTTP layer.
    """

    def test_timeout_result_has_typed_message(self):
        """asyncio.TimeoutError → ScanResult(TIMEOUT) với TargetSiteTimeout str."""
        import asyncio
        from unittest.mock import AsyncMock, patch, MagicMock
        from Core.engine.async_search import search_site, SiteConfig
        from Core.models import ScanResult, ScanStatus, ErrorStrategy

        site = SiteConfig(
            name="GitHub",
            url_template="https://github.com/{}",
            display_url="https://github.com/testuser",
            error_strategy=ErrorStrategy.STATUS_CODE,
        )

        async def run():
            mock_session = MagicMock()
            mock_session.get = MagicMock()
            mock_session.get.return_value.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=False)
            return await search_site(mock_session, site, "testuser")

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.TIMEOUT
        assert "TargetSiteTimeout" in result.error_message

    def test_generic_error_result_has_typed_message(self):
        """Generic Exception → ScanResult(ERROR) với SiteCheckError str."""
        import asyncio
        from unittest.mock import AsyncMock, MagicMock
        from Core.engine.async_search import search_site, SiteConfig
        from Core.models import ScanStatus, ErrorStrategy

        site = SiteConfig(
            name="Reddit",
            url_template="https://reddit.com/u/{}",
            display_url="https://reddit.com/u/testuser",
            error_strategy=ErrorStrategy.STATUS_CODE,
        )

        async def run():
            mock_session = MagicMock()
            mock_session.get = MagicMock()
            mock_session.get.return_value.__aenter__ = AsyncMock(
                side_effect=ConnectionError("network unreachable")
            )
            mock_session.get.return_value.__aexit__ = AsyncMock(return_value=False)
            return await search_site(mock_session, site, "testuser")

        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.ERROR
        assert "SiteCheckError" in result.error_message
