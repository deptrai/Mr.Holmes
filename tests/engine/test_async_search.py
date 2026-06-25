"""
tests/engine/test_async_search.py

Unit tests cho Core/engine/async_search.py.
Story 2.1 — Migrate Requests_Search → aiohttp Async Method, Epic 2.

Test coverage:
    - search_site() với 3 error strategies (Status-Code, Message, Response-Url)
    - SiteConfig dataclass
    - Timeout handling
    - Error handling (network exception)

Migrated from aioresponses to unittest.mock (aioresponses incompatible
with aiohttp 3.11+).
"""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from tests.conftest import make_mock_response, make_mock_session

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


def _run_with_mock_session(mock_session, site, username="testuser"):
    """Run search_site with a mock session via asyncio."""
    async def _run():
        return await search_site(mock_session, site, username)
    return asyncio.new_event_loop().run_until_complete(_run())


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
        resp = make_mock_response(status=200, body=b"<html>Profile</html>")
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.status == ScanStatus.FOUND
        assert result.site_name == "TestSite"
        assert result.url == site.display_url

    def test_status_404_returns_not_found(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_mock_response(status=404)
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.status == ScanStatus.NOT_FOUND

    def test_status_204_returns_not_found(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_mock_response(status=204)
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.status == ScanStatus.NOT_FOUND

    def test_other_status_returns_error(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_mock_response(status=503)
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.status == ScanStatus.ERROR
        assert "503" in result.error_message

    def test_found_result_includes_tags(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE, tags=["Dev", "Code"])
        resp = make_mock_response(status=200, body=b"<html>Profile</html>")
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.tags == ["Dev", "Code"]

    def test_found_result_is_scrapable(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE, is_scrapable=True)
        resp = make_mock_response(status=200, body=b"<html>Profile</html>")
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.is_scrapable is True


# ---------------------------------------------------------------------------
# Strategy: Message
# ---------------------------------------------------------------------------

class TestMessageStrategy:
    """AC2 — Message error strategy: error_text NOT in body → found."""

    def test_error_text_not_in_body_returns_found(self):
        site = make_site(strategy=ErrorStrategy.MESSAGE, error_text="Profile not found")
        resp = make_mock_response(status=200, body="Welcome to testuser's page!")
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.status == ScanStatus.FOUND

    def test_error_text_in_body_returns_not_found(self):
        site = make_site(strategy=ErrorStrategy.MESSAGE, error_text="Profile not found")
        resp = make_mock_response(status=200, body="Profile not found - user does not exist")
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
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
        # response.url is the default "https://example.com/testuser" which != response_url
        resp = make_mock_response(status=200, body=b"<html>Profile</html>", url="https://example.com/testuser")
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
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

        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.url = expected_url  # str matches response_url
        mock_resp.headers = {}
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        session = MagicMock()
        session.get = MagicMock(return_value=mock_resp)

        result = _run_with_mock_session(session, site)
        assert result.status == ScanStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

class TestErrorHandling:
    """Timeout và network errors gracefully return ScanResult(ERROR/TIMEOUT)."""

    def test_network_exception_returns_error_result(self):
        """Generic exception → ScanResult ERROR, không raise."""
        site = make_site()

        session = MagicMock()
        session.get = MagicMock(side_effect=Exception("connection refused"))

        result = _run_with_mock_session(session, site)
        assert result.status == ScanStatus.ERROR
        assert result.site_name == "TestSite"

    def test_timeout_returns_timeout_status(self):
        """asyncio.TimeoutError → ScanResult TIMEOUT (H1 fix verification)."""
        site = make_site()

        session = MagicMock()
        session.get = MagicMock(side_effect=asyncio.TimeoutError())

        result = _run_with_mock_session(session, site)
        assert result.status == ScanStatus.TIMEOUT
        # Story 2.4: error_message now uses TargetSiteTimeout structured format
        assert "TargetSiteTimeout" in result.error_message

    def test_empty_error_text_returns_error(self):
        """MESSAGE strategy with empty error_text → ScanResult ERROR (M2 fix verification)."""
        site = make_site(strategy=ErrorStrategy.MESSAGE, error_text="")
        resp = make_mock_response(status=200, body="Some page content")
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.status == ScanStatus.ERROR
        assert "error_text" in result.error_message


# ---------------------------------------------------------------------------
# ScanResult interface (AC3 + AC5)
# ---------------------------------------------------------------------------

class TestScanResultInterface:
    """AC3 — ScanResult dataclass tích hợp. AC5 — không mutate shared lists."""

    def test_returns_scan_result_instance(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_mock_response(status=200, body=b"<html>Profile</html>")
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert isinstance(result, ScanResult)

    def test_found_property_on_found_result(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_mock_response(status=200, body=b"<html>Profile</html>")
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.found is True

    def test_not_found_result_found_false(self):
        site = make_site(strategy=ErrorStrategy.STATUS_CODE)
        resp = make_mock_response(status=404)
        session = make_mock_session(resp)
        result = _run_with_mock_session(session, site)
        assert result.found is False
