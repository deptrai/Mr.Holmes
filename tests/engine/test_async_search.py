"""
tests/engine/test_async_search.py

Unit tests cho Core/engine/async_search.py.
Story 2.1 — Migrate Requests_Search → aiohttp Async Method, Epic 2.

Test coverage:
    - search_site() với 3 error strategies (Status-Code, Message, Response-Url)
    - SiteConfig dataclass
    - Timeout handling
    - Error handling (network exception)
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aioresponses import aioresponses

from Core.engine.async_search import search_site, SiteConfig
from Core.models import ScanResult, ScanStatus, ErrorStrategy


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_site(
    name="TestSite",
    url="https://example.com/testuser",
    strategy=ErrorStrategy.STATUS_CODE,
    error_text="",
    response_url="",
    tags=None,
    is_scrapable=False,
) -> SiteConfig:
    return SiteConfig(
        name=name,
        url_template="https://example.com/{}",
        display_url=url,
        error_strategy=strategy,
        error_text=error_text,
        response_url=response_url,
        tags=tags or ["Tech"],
        is_scrapable=is_scrapable,
    )


# ---------------------------------------------------------------------------
# SiteConfig dataclass
# ---------------------------------------------------------------------------

class TestSiteConfig:
    def test_defaults(self):
        site = make_site()
        assert site.error_text == ""
        assert site.response_url == ""
        assert site.is_scrapable is False
        assert site.tags == ["Tech"]

    def test_explicit_fields(self):
        site = make_site(
            strategy=ErrorStrategy.MESSAGE,
            error_text="Not found",
            tags=["Developer", "Code"],
            is_scrapable=True,
        )
        assert site.error_strategy == ErrorStrategy.MESSAGE
        assert site.error_text == "Not found"
        assert site.is_scrapable is True


# ---------------------------------------------------------------------------
# Strategy: Status-Code
# ---------------------------------------------------------------------------

class TestStatusCodeStrategy:
    """AC2 — Status-Code error strategy hoạt động identical với requests."""

    def test_status_200_returns_found(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        with aioresponses() as m:
            m.get(site.display_url, status=200)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.FOUND
        assert result.site_name == "TestSite"
        assert result.url == site.display_url

    def test_status_404_returns_not_found(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        with aioresponses() as m:
            m.get(site.display_url, status=404)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.NOT_FOUND

    def test_status_204_returns_not_found(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        with aioresponses() as m:
            m.get(site.display_url, status=204)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.NOT_FOUND

    def test_other_status_returns_error(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        with aioresponses() as m:
            m.get(site.display_url, status=503)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.ERROR
        assert "503" in result.error_message

    def test_found_result_includes_tags(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE, tags=["Dev", "Code"])
        with aioresponses() as m:
            m.get(site.display_url, status=200)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.tags == ["Dev", "Code"]

    def test_found_result_is_scrapable(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE, is_scrapable=True)
        with aioresponses() as m:
            m.get(site.display_url, status=200)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.is_scrapable is True


# ---------------------------------------------------------------------------
# Strategy: Message
# ---------------------------------------------------------------------------

class TestMessageStrategy:
    """AC2 — Message error strategy: error_text NOT in body → found."""

    def test_error_text_not_in_body_returns_found(self):
        site = make_site(strategy=ErrorStrategy.MESSAGE, error_text="Profile not found")
        with aioresponses() as m:
            m.get(site.display_url, status=200, body="Welcome to testuser's page!")
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.FOUND

    def test_error_text_in_body_returns_not_found(self):
        site = make_site(strategy=ErrorStrategy.MESSAGE, error_text="Profile not found")
        with aioresponses() as m:
            m.get(site.display_url, status=200, body="Profile not found - user does not exist")
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# Strategy: Response-Url
# ---------------------------------------------------------------------------

class TestResponseUrlStrategy:
    """AC2 — Response-Url strategy: actual URL != expected URL → found."""

    def test_url_different_from_expected_returns_found(self):
        site = make_site(
            url="https://example.com/testuser",
            strategy=ErrorStrategy.RESPONSE_URL,
            response_url="https://example.com/404",
        )
        # Mock target_url (url_template.format(username)), not display_url
        target_url = site.url_template.format("testuser")
        with aioresponses() as m:
            m.get(target_url, status=200)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.FOUND


    def test_url_matches_expected_returns_not_found(self):
        """
        Response-Url strategy: nếu site redirect đến response_url → NOT_FOUND.
        Simulate redirect bằng cách mock response.url trả về response_url.
        """
        expected_url = "https://example.com/404"
        site = make_site(
            url=expected_url,
            strategy=ErrorStrategy.RESPONSE_URL,
            response_url=expected_url,
        )
        target_url = site.url_template.format("testuser")

        import aiohttp
        async def run():
            async with aiohttp.ClientSession() as session:
                # Tạo mock response với url = response_url (simulate redirect)
                mock_resp = AsyncMock()
                mock_resp.status = 200
                mock_resp.url = MagicMock()
                mock_resp.url.__str__ = MagicMock(return_value=expected_url)
                mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
                mock_resp.__aexit__ = AsyncMock(return_value=False)
                with patch.object(session, "get", return_value=mock_resp):
                    return await search_site(session, site, "testuser")
        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.NOT_FOUND




# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Timeout và network errors gracefully return ScanResult(ERROR/TIMEOUT)."""

    def test_network_exception_returns_error_result(self):
        """Generic exception → ScanResult ERROR, không raise."""
        import aiohttp
        site = make_site()

        async def run():
            async with aiohttp.ClientSession() as session:
                with patch.object(session, "get", side_effect=Exception("connection refused")):
                    return await search_site(session, site, "testuser")
        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.ERROR
        assert result.site_name == "TestSite"

    def test_timeout_returns_timeout_status(self):
        """asyncio.TimeoutError → ScanResult TIMEOUT (H1 fix verification)."""
        import aiohttp as _aiohttp
        site = make_site()

        async def run():
            async with _aiohttp.ClientSession() as session:
                with patch.object(session, "get", side_effect=asyncio.TimeoutError()):
                    return await search_site(session, site, "testuser")
        result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.TIMEOUT
        # Story 2.4: error_message now uses TargetSiteTimeout structured format
        assert "TargetSiteTimeout" in result.error_message

    def test_empty_error_text_returns_error(self):
        """MESSAGE strategy with empty error_text → ScanResult ERROR (M2 fix verification)."""
        site = make_site(strategy=ErrorStrategy.MESSAGE, error_text="")
        with aioresponses() as m:
            m.get(site.display_url, status=200, body="Some page content")
            import aiohttp as _aiohttp
            async def run():
                async with _aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.status == ScanStatus.ERROR
        assert "error_text" in result.error_message


# ---------------------------------------------------------------------------
# ScanResult interface (AC3 + AC5)
# ---------------------------------------------------------------------------

class TestScanResultInterface:
    """AC3 — ScanResult dataclass tích hợp. AC5 — không mutate shared lists."""

    def test_returns_scan_result_instance(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        with aioresponses() as m:
            m.get(site.display_url, status=200)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert isinstance(result, ScanResult)

    def test_found_property_on_found_result(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        with aioresponses() as m:
            m.get(site.display_url, status=200)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.found is True

    def test_not_found_result_found_false(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        with aioresponses() as m:
            m.get(site.display_url, status=404)
            import aiohttp
            async def run():
                async with aiohttp.ClientSession() as session:
                    return await search_site(session, site, "testuser")
            result = asyncio.get_event_loop().run_until_complete(run())
        assert result.found is False
