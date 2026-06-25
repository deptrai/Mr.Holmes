"""
tests/engine/test_search_strategies.py

Tests cho 3 error strategies dùng shared conftest fixtures và mock-based
HTTP mocking.

Story 4.1 — AC5: ≥ 3 test cases cho 3 error strategies.
Demonstrates: conftest shared fixtures + unittest.mock HTTP mocking pattern.

Migrated from aioresponses to unittest.mock (aioresponses incompatible
with aiohttp 3.11+).
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from tests.conftest import make_mock_response, make_mock_session

from Core.engine.async_search import search_site
from Core.models.scan_result import ScanStatus


# ---------------------------------------------------------------------------
# Status-Code strategy tests (AC5)
# ---------------------------------------------------------------------------

class TestStatusCodeStrategyWithFixtures:
    """Dùng conftest fixtures: status_code_site + mock_session."""

    @pytest.mark.asyncio
    async def test_status_code_found(self, status_code_site) -> None:
        """Status-Code: HTTP 200 với body sạch → FOUND."""
        resp = make_mock_response(status=200, body=b"<html>Profile</html>")
        session = make_mock_session(resp)
        result = await search_site(session, status_code_site, "johndoe")
        assert result.status == ScanStatus.FOUND

    @pytest.mark.asyncio
    async def test_status_code_not_found(self, status_code_site) -> None:
        """Status-Code: HTTP 404 → NOT_FOUND."""
        resp = make_mock_response(status=404)
        session = make_mock_session(resp)
        result = await search_site(session, status_code_site, "johndoe")
        assert result.status == ScanStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_status_code_rate_limited(self, status_code_site) -> None:
        """Status-Code: HTTP 429 → RATE_LIMITED."""
        resp = make_mock_response(status=429)
        session = make_mock_session(resp)
        result = await search_site(session, status_code_site, "johndoe")
        assert result.status == ScanStatus.RATE_LIMITED


# ---------------------------------------------------------------------------
# Message strategy tests (AC5)
# ---------------------------------------------------------------------------

class TestMessageStrategyWithFixtures:
    """Dùng conftest fixture: message_site."""

    @pytest.mark.asyncio
    async def test_message_found(self, message_site) -> None:
        """Message: body không chứa error_text → FOUND."""
        resp = make_mock_response(status=200, body=b"<html>Welcome johndoe</html>")
        session = make_mock_session(resp)
        result = await search_site(session, message_site, "johndoe")
        assert result.status == ScanStatus.FOUND

    @pytest.mark.asyncio
    async def test_message_not_found(self, message_site) -> None:
        """Message: body chứa error_text → NOT_FOUND."""
        resp = make_mock_response(status=200, body=b"User not found")
        session = make_mock_session(resp)
        result = await search_site(session, message_site, "johndoe")
        assert result.status == ScanStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# Response-Url strategy tests (AC5)
# ---------------------------------------------------------------------------

class TestResponseUrlStrategyWithFixtures:
    """Dùng conftest fixture: response_url_site."""

    @pytest.mark.asyncio
    async def test_response_url_found(self, response_url_site) -> None:
        """Response-Url: final URL khác expected_url → FOUND."""
        # response_url_site.response_url = "https://example.com/404"
        # The actual URL (from url_template.format) is "https://example.com/johndoe"
        # which != response_url, so → FOUND
        resp = make_mock_response(
            status=200,
            body=b"<html>Profile</html>",
            url="https://example.com/johndoe",
        )
        session = make_mock_session(resp)
        result = await search_site(session, response_url_site, "johndoe")
        assert result.status == ScanStatus.FOUND

    @pytest.mark.asyncio
    async def test_response_url_not_found(self, response_url_site) -> None:
        """Response-Url: final URL == response_url → NOT_FOUND.

        Dùng unittest.mock trực tiếp để control response.url.
        """
        mock_resp = MagicMock(
            status=200,
            url=response_url_site.response_url,
            headers={},
        )
        mock_resp.text = AsyncMock(return_value="Not found")
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)
        session = MagicMock()
        session.get = MagicMock(return_value=mock_resp)

        result = await search_site(session, response_url_site, "johndoe")
        assert result.status == ScanStatus.NOT_FOUND
