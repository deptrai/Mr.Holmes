"""
tests/engine/test_search_strategies.py

Tests cho 3 error strategies dùng shared conftest fixtures và aioresponses.

Story 4.1 — AC5: ≥ 3 test cases cho 3 error strategies.
Demonstrates: conftest shared fixtures + aioresponses HTTP mocking pattern.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from Core.engine.async_search import search_site
from Core.models.scan_result import ScanStatus


# ---------------------------------------------------------------------------
# Status-Code strategy tests (AC5)
# ---------------------------------------------------------------------------

class TestStatusCodeStrategyWithFixtures:
    """Dùng conftest fixtures: status_code_site + mock_aiohttp."""

    @pytest.mark.asyncio
    async def test_status_code_found(self, status_code_site, mock_aiohttp) -> None:
        """Status-Code: HTTP 200 với body sạch → FOUND."""
        import aiohttp
        mock_aiohttp.get(status_code_site.url_template.format("johndoe"), status=200, body=b"<html>Profile</html>")
        async with aiohttp.ClientSession() as session:
            result = await search_site(session, status_code_site, "johndoe")
        assert result.status == ScanStatus.FOUND

    @pytest.mark.asyncio
    async def test_status_code_not_found(self, status_code_site, mock_aiohttp) -> None:
        """Status-Code: HTTP 404 → NOT_FOUND."""
        import aiohttp
        mock_aiohttp.get(status_code_site.url_template.format("johndoe"), status=404)
        async with aiohttp.ClientSession() as session:
            result = await search_site(session, status_code_site, "johndoe")
        assert result.status == ScanStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_status_code_rate_limited(self, status_code_site, mock_aiohttp) -> None:
        """Status-Code: HTTP 429 → RATE_LIMITED."""
        import aiohttp
        mock_aiohttp.get(status_code_site.url_template.format("johndoe"), status=429)
        async with aiohttp.ClientSession() as session:
            result = await search_site(session, status_code_site, "johndoe")
        assert result.status == ScanStatus.RATE_LIMITED


# ---------------------------------------------------------------------------
# Message strategy tests (AC5)
# ---------------------------------------------------------------------------

class TestMessageStrategyWithFixtures:
    """Dùng conftest fixture: message_site + mock_aiohttp."""

    @pytest.mark.asyncio
    async def test_message_found(self, message_site, mock_aiohttp) -> None:
        """Message: body không chứa error_text → FOUND."""
        import aiohttp
        mock_aiohttp.get(message_site.url_template.format("johndoe"), status=200, body=b"<html>Welcome johndoe</html>")
        async with aiohttp.ClientSession() as session:
            result = await search_site(session, message_site, "johndoe")
        assert result.status == ScanStatus.FOUND

    @pytest.mark.asyncio
    async def test_message_not_found(self, message_site, mock_aiohttp) -> None:
        """Message: body chứa error_text → NOT_FOUND."""
        import aiohttp
        mock_aiohttp.get(message_site.url_template.format("johndoe"), status=200, body=b"User not found")
        async with aiohttp.ClientSession() as session:
            result = await search_site(session, message_site, "johndoe")
        assert result.status == ScanStatus.NOT_FOUND


# ---------------------------------------------------------------------------
# Response-Url strategy tests (AC5)
# ---------------------------------------------------------------------------

class TestResponseUrlStrategyWithFixtures:
    """Dùng conftest fixture: response_url_site."""

    @pytest.mark.asyncio
    async def test_response_url_found(self, response_url_site, mock_aiohttp) -> None:
        """Response-Url: final URL khác expected_url → FOUND."""
        import aiohttp
        mock_aiohttp.get(
            response_url_site.url_template.format("johndoe"),
            status=200,
            body=b"<html>Profile</html>",
        )
        async with aiohttp.ClientSession() as session:
            result = await search_site(session, response_url_site, "johndoe")
        assert result.status == ScanStatus.FOUND

    @pytest.mark.asyncio
    async def test_response_url_not_found(self, response_url_site) -> None:
        """Response-Url: final URL == response_url → NOT_FOUND.

        Dùng unittest.mock trực tiếp vì aioresponses không control response.url.
        """
        mock_resp = MagicMock(
            status=200,
            url=MagicMock(__str__=MagicMock(return_value=response_url_site.response_url)),
            headers={},
            text=AsyncMock(return_value="Not found"),
        )
        mock_ctx = MagicMock(
            __aenter__=AsyncMock(return_value=mock_resp),
            __aexit__=AsyncMock(return_value=False),
        )
        session = MagicMock()
        session.get = MagicMock(return_value=mock_ctx)

        result = await search_site(session, response_url_site, "johndoe")
        assert result.status == ScanStatus.NOT_FOUND
